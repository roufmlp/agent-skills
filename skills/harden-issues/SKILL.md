---
name: harden-issues
description: Attack acceptance criteria at authoring time — a blind-spot pass over issue files that sharpens criteria with evidence, names invariants, and routes open forks to the human. EXPLICIT INVOCATION ONLY. Use this skill only when the user types the command /harden-issues, or when an upstream issue-drafting pass calls it on freshly drafted slices. Never infer it from wording such as "harden these issues", "pre-batch pass" or "attack the criteria".
argument-hint: "a named batch — issue numbers or a range — or nothing when invoked on drafts by an upstream tool"
---

# Harden issues

Attack acceptance criteria before anyone builds to them. An issue whose criteria
are wrong when written passes every gate — the implementer builds to the bad spec
and both gates grade against that same bad spec. This pass is the early fix.
It is also what buys the next run an uninterrupted one: anything the run would
otherwise stop and ask a human for is settled here, while a human is at the
keyboard (see "Checks only the human can run"). Provenance and the incident
record live in this directory's `decisions.md`; read it when changing this
skill, not when running it.

Two entry points, same pass:

- **From an upstream issue-drafting pass, if the project has one** — runs on the
  drafted slices before the user quiz; the pass's questions join that quiz.
- **Standalone, pre-batch** — runs once over **a named batch**, immediately before
  `/run-issues` takes that same batch; questions come back as one numbered list.
  `needs-harden` is what a run sets when it finds criteria that are wrong or stale,
  so those issues return here rather than resting.

  **It takes a batch list, never `all`.** The pass used to gate every issue at the
  moment it was written, which is how a queue of issues built up that could not run
  because hardening stops on questions only the human can rule. Hardening is now
  bought for the issues about to be built, and nothing else. An issue nobody has
  scheduled does not need sharpening yet.

## Write authority — the one rule that matters

The pass may edit an issue file **only where it can cite verification**: a
file:line in current code, a query against real data, or a measured value. The
same bar the run gates use. Everything else — and **every open fork** — becomes a
numbered question for the human. The pass never settles a fork by choice.

Any road-shaped statement it writes ("the rule is X", "the cause is Y") is a
hypothesis unless its premise was tested. Untested → write it as a hypothesis
with an explicit premise-check clause for the implementer, testing the premise
itself, not a narrow question near it.

## Fan-out

**A prohibition in a brief names the SYSTEM, not the verb.** Every "do not" carries the
forbidden thing AND the permitted one, with an absolute path wherever a path exists. Three
faults in one `/run-issues` batch shared one shape: "QA is the only WRITABLE
database" constrained the operation and left production reachable, so a verify gate read
production with a service-role key; "a probe script needs a directory holding `node_modules`"
named no home, so three files landed at the shared worktree root; and a brief naming no
register path sent two gates to the worktree copy instead of the main checkout's. A brief
that constrains the ACT while leaving the PLACE unnamed gets a different answer from every
agent. (Adopted 2026-08-09.)

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
`.scratch/<feature>/harden/seam.md`. The pass reads counts, questions and each
findings file's `## Checks for the human` section, never the working.

**On each attacker return, check the file exists and holds something — before
the seam agent spawns, and before anything is stamped:**

```bash
python3 ~/.claude/skills/lib/check_verdict.py --file .scratch/<feature>/harden/<issue>.md
```

A non-zero exit means that attacker produced nothing, whatever its final message
said, so the issue was not hardened. Re-spawn it, or leave the issue unstamped
and name it as unattacked. **An issue nobody attacked is never stamped
`ready-for-agent`**: the stamp is what puts it in the next run's scope, so a
silent gap here ships exactly the bad spec this pass exists to catch. A missing
file also narrows the seam agent's input without saying so.

Two adversarial gates died at the weekly usage limit during one workflow audit
and wrote nothing at all. Nothing mechanical noticed either time.

**Model: inherit.** Both agent files carry `model: inherit`, so the pass runs on
the tier the session was launched on. A second, differently-tuned model was
pinned here once, for blind-spot hunting; the pin is gone because it hid the
choice inside an agent file and it was credit-gated. To harden on a different
model, launch the session on it. Effort stays `high`, not `max`: the checklist
is enumeration against a file, and enumeration is recall rather than chained
reasoning.

**Print one launch line before spawn #1, on every invocation** — the resolved
session model, the issues in scope, and how many attackers are about to spawn.
Never pass a `model:` value on a spawn: the spawn tool's `model` parameter beats
agent-file frontmatter, so a spawn-time value defeats `inherit` silently and
nothing downstream records which tier ran. The launch line is the one place a
wrong tier is visible, and the stamp does not carry it. Not a wait, an interrupt
window — do not ask, and do not stall for an answer.

**Never attack an issue a run holds.** The guard keys on the run, not on the
issue's status: skip anything whose row in the same directory's `run.md` is past
`queued`, and skip everything if that ledger's owner line names a live session.
`needs-harden` and `ready-for-agent` are both in scope — `needs-harden` is what a
run sets when it finds criteria that are wrong or stale, so those issues are
exactly what this pass exists to serve, and a status-shaped guard would tell it to
skip them. What the guard protects against is a second writer: rewriting criteria
under a working implementer causes a rejection on correct work, then a strike,
then an escalation chasing a criterion the implementer never saw.

**The one exception: strike-2 mode.** A `/run-issues` runner may spawn a single
attacker against an issue it holds, after two rejections, before it buys a third
implementer. The guard above protects against a second writer, and at that moment
there is none — the implementer is dead and the runner spawns nothing else until
the attacker returns. Strike-2 mode is narrower than a normal pass: classes 1, 5
and 9 only, evidence or silence, and **it never waits for an answer** — an
unsettled fork returns as a blocked issue, not a question the run sits on.

## The attack checklist

Earned, not invented — each class shipped a real defect through green gates in the
July 2026 runs (the incident behind each is in `decisions.md`). The attacker works
the list against the issue AND the current code/data, and reports per class:
sharpened (with evidence), question (for the human), or clean.

1. **Unstated invariants.** What must NOT change. Name the neighbouring behaviours
   the slice sits beside — paging, limits, ordering, counts, permissions — and
   write them into `## Must still be true`.
2. **Invariant scope.** Every invariant states who it covers: all callers,
   including ones routed in by other issues later.
3. **Vague words.** "Consistent", "bounded", "handled", "a recovery affordance" —
   each criterion must name a fixture and an answer.

   **A criterion may not be graded against a list of instances.** Class 3 catches
   a criterion that is too loose; this catches the opposite failure — one pinned
   to the examples instead of to the rule behind them. "These four call sites use
   the admin client" passes the moment a fifth is added, and the issue ships with
   its own hole. Write the rule, then name the instances as evidence that the
   rule bites today. (Adopted 2026-08-07, from a run finale; three implementers
   warned about this class avoided it three for three.)

   **A criterion that moves security-relevant code pins the property, not the
   count of surviving tests.** The surviving tests are one more list of instances,
   and "the existing tests keep passing" grades the move against that list rather
   than against the rule the moved code holds. Name the property the code must
   still hold — "a caller-supplied needle deletes only what it literally matches" —
   and name a hostile input and an over-long input the criterion covers. (Adopted
   2026-08-18, from one run. One issue moved the auth failure sanitiser into a
   shared module so the unauthenticated confirm route could use it. Its
   criterion graded the move by the surviving tests. The implementer replaced a
   literal sanitiser with a pattern built per character, and all 69 tests passed.
   The critical review gate then drove two live defects on that route: a needle
   of about 1000 characters built a regex V8 refuses to
   compile, so the route returned HTTP 500 **and logged nothing**, because its own
   `catch` called the throwing function again; and the separator tolerance let a
   crafted `token_hash` delete the real message out of the log line. Strike 1, one
   retry, 89 minutes against an estimate of 30 to 45. The 21-item verify pass
   missed both, and the gate said why: a permissive-regex swap satisfies "the
   existing tests keep passing" while changing behaviour.)
4. **Guards that cannot fail.** Each criterion states how a violation would be
   observed. Prefer mutation-shaped criteria — "reds when X is deliberately
   reintroduced" — where cheap.

   **A criterion that names a mutation must have that mutation driven once
   before the issue ships.** Not described, driven: make the change, watch the
   test red, put it back, watch it green. An undriven mutation is a guard nobody
   has proved can fail, which is the class this whole entry exists to close.
   (Adopted 2026-08-07.)

   **A criterion may never ask for evidence to land somewhere the party it names
   cannot write.** Read the clause, name its writer, and check that writer's
   pen. Two homes fail today: an implementer writes neither the issue file nor
   the commit message. Send the evidence to a test, a doc comment, the register
   or the merge briefing — all four survive a run's own write rules. Where the
   evidence genuinely belongs in one of the closed homes, address the clause to
   the party that holds that pen, which for a commit message is the runner and
   for a verdict is the gate.

   The check is mechanical, because the clause names its own writer. Refuse it
   here, at authoring time. (Adopted 2026-08-10 for the issue file, from a run
   finale: one issue's criteria asked for mutation drives "recorded in the
   issue's notes", the spawn brief forbade it, the drives went into test doc
   comments, and the review gate filed the contradiction. **Widened 2026-08-16
   to any closed home, after a later run:** five of its nine issues carried a
   clause aimed at the implementer, and the commit-message half fell outside
   the 2026-08-10 wording. One issue's review gate rejected the work partly
   because those clauses were unmet, and the runner had to annul the ground.
   One annulled rejection and one wasted gate round, in one batch.)

   **A constraint taken from measured data is labelled as one.** Where a criterion
   or an invariant fixes a number because that is what today's input holds, write
   it into `## Must still be true` as an assumption a later issue may need to
   lift, and say the migration header must do the same. (Adopted 2026-08-10, from
   the same run finale. The run-issues copy carries the incident.)
5. **Unverified premises.** Every factual claim in the issue — counts, "both
   bots", "the DB splits case variants", any impossibility claim — verified
   against the real code or data.

   **A negative claim ships with the command that establishes it, or it is
   deleted.** "Nothing else calls this", "no other table has the grant", "the
   platform cannot do X" — paste the grep, the query or the doc read that proves
   it, beside the claim. Flagging is no longer enough for this shape: an
   impossibility claim with no command behind it comes out of the issue
   altogether, because a reader cannot tell a checked negative from a guessed one
   and will act on both. Narrowing it is not the remedy; deleting it is. (Adopted
   2026-08-07. This edits class 5 deliberately and must never become a class of
   its own — two homes for impossibility claims is the drift it avoids.)
6. **Empty or missing hostile data.** Does QA/production hold data that can
   exercise each criterion? If not, say so and name the fixture to create —
   otherwise the gates validate over an empty set.
7. **Deploy and boundary reality.** Migration ordering (one-way? code-first or
   db-first?), client/server module boundary, platform caps.
8. **Observability.** How will each criterion be verified, and is the property
   observable to a gate or a walk at all? A criterion nobody can observe is not a
   criterion.
9. **Size against the one-implementer bound.** A clean issue runs ~30-90 min;
   suspect anything whose criteria span several independent deliverables, or that
   packs migration + logic + UI into one slice. Propose the cut line — where one
   half ships and gates alone ("extract + harness", then "behavioural tests") —
   as a question for the human; splitting is their call, never the pass's or the
   runner's. `/run-issues` deliberately never splits mid-run — an oversized
   issue that reaches a runner arrives back here.

10. **The database the rows land in.** An issue whose work writes data rows — an
    import, a seed, a backfill, a migration carrying data — names every database
    those rows must reach, in `## Target database`: each by project ref, the owner
    who may write it, the moment it happens, and the route. An issue that changes
    code only answers `Writes rows: no`.

    **A criterion that counts rows or reads data names its database.** A gate
    grades one criterion at a time and reaches whichever database it is allowed to
    write, so "the target database" resolves to that one and reads green wherever
    it runs. This class adds the ref and nothing else — the count itself stays
    governed by classes 3 and 4, which keep it derived from its source rather than
    frozen at today's figure.

    **A criterion may name only work the run can do.** Where a database is
    reachable by the human alone, that step goes to the project's pending-actions
    file, if the project keeps one, as a numbered action, and `## Target database`
    records the intent. Same reason as class 4's rule on evidence in the issue
    file: an agent cannot meet a criterion aimed at somebody else.

    Unanswered, this defaults: the writable database during the run, then the
    production database, owner the human, after the deploy — written as a default.
    Silence is what this class exists to catch, so a pending action nobody needed
    is the cheap error. (Adopted 2026-08-12; the incident is in `decisions.md`.)

The seam agent adds: gaps that fall between two issues, invariants one issue
scopes that another widens, and accidental dependencies (a fix that holds only
because of something a sibling issue deletes).

## Repair the stale citations first, before anybody attacks the file

A citation that moved reads as a wrong premise, and an attacker spends a round
on it. Where the repo carries the script, run it over each issue in scope before
the attackers spawn:

```
node scripts/check-issue-citations.mjs --quiet <each issue file>
```

Correct every `moved` row to the line it reports. Read every `gone` row rather
than deleting it — the line may have been rewritten, or the citation may always
have been wrong, and those are different repairs. `unknown` means the check
could not run and is not a fault.

**This pass is where the repair happens (ruled 2026-08-15).** A run may not
write an issue file, so `/run-issues` reports these and leaves them; one run
left eight. You already read the whole file and you are already allowed to
write it, so the fix costs nothing extra here and costs a round everywhere
else. A `holds` is not proof: the check compares against the commit that last
touched the citation's own line, so a citation rewritten without re-checking
its number can read `holds` and still be wrong.

## Output and the stamp

- Evidence-backed sharpenings are edited into `## Acceptance criteria` and
  `## Must still be true` directly, each carrying its citation.
- **Say how many citations were repaired** in the stamp line below, so a reader
  can tell a quiet pass from one that found nothing.
- **Every question ships with the pass's recommended answer**, and is marked
  `[reversible]` or `[irreversible]` — per the project's question standard, if
  it keeps one. A question with no default is a question the pass has not
  finished thinking about.
- Questions go to the human: into the upstream drafting tool's quiz, if there is
  one, or as the standalone numbered list. Apply their answers to the files.
- Then stamp the issue, one line under `Status:`:
  `Hardened: <date> — <n> sharpened, <m> questions resolved.`
- **Stamping also sets `Status: ready-for-agent`.** The two must agree, and the
  stamp alone is not enough: `/run-issues` resolves `all` from the `Status:`
  line and skips anything reading `needs-*`, so an issue that entered through
  the standalone door and keeps its `needs-harden` status is silently dropped
  from the next batch while this pass reports it ready. Keep any minting or
  provenance note on its own `Provenance:` line, never as a suffix on `Status:`.

**An open question never removes an issue from a run.** Where the human has not
answered, take the recommended default, write it into the file as a default rather
than a decision, and stamp — status included, same rule:

`Hardened (provisional): <date> — <n> sharpened, <m> defaults pending.`

A provisionally stamped issue is in scope for `/run-issues`' own `all`, and the merge
briefing names every one that shipped that way, so the answer arrives after the run
instead of holding it up. Two things are not defaultable: an `[irreversible]`
question, and a split — both leave the issue unstamped, and out of that scope until
the human rules. This pass has no `all` of its own; it takes the batch it was given.

Every defaulted question is also appended to `.scratch/decisions-queue.md`, the
one place every tool upstream of this pass queues decisions, so they reach the
human in a single list rather than scattered across issue files.

Where an answer needs input nobody here has — a third party, a credential, a
product call with no defensible default — set `needs-harden` instead, so the issue
comes back to this pass rather than dying in a status nothing reads.

`/run-issues` lists unstamped scoped issues in its launch message — a launch-time
line for the human, never a gate, never mid-run.

## Checks only the human can run happen here, not mid-run

A criterion that waits on a value only the human can fetch — a row in the
production database, a setting in a provider console, anything behind a credential
the agents do not hold — costs the run an unattended stall if it survives this
pass. The hardening session is attended. Settle it here.

- **Collect them as you attack.** An attacker that cannot verify a premise because
  the check is out of its reach records a check, not a question: what to run or look
  at, where, and which criterion in which issue the answer decides. Both agent types
  write them under `## Checks for the human` in their findings file, which is where
  this session reads them.
- **Run everything you can run yourself first.** A QA environment is usually
  writable, the code is readable, most premises need nobody. The list the human
  sees carries only what the repo's rules or the credentials put out of your hands,
  and each item says in one clause why it is theirs.
- **Put the list to them at the end of the pass, in the same session as the
  questions.** Numbered, one action per item, and for any provider console the
  current official button names, read from the provider's live documentation rather
  than from memory.
- **Write their results into the issue files as facts**, cited `checked by the
  human <date>` with the query or the setting quoted. That citation meets the
  write-authority bar the same way a file:line does.
- **No hardened issue may ask the run to stop for a human.** A criterion that tells
  the implementer to run a script and report the output, or to pause for a value, is
  a defect in the issue. Either the check happens here and the answer goes into the
  file, or the criterion is rewritten so the implementer and the gates settle it
  alone.
- **If the human is away, or waves the list off**, the default road applies
  unchanged: take the default, write it as a default, queue it to
  `.scratch/decisions-queue.md`. A check nobody ran never holds the batch.

## Scope notes

Issue trackers are per-project — this pack's convention is
`.scratch/<feature>/issues/`. The pass edits issue files only — never code, never
the tracker board, never another skill's state.

**The pass never mints.** It sharpens the issues it was given and creates none. This
rule was already written and the practice ran ahead of it anyway: one pass cleared
two issues out of `needs-harden` and minted two more into it, leaving the queue
exactly where it started. Where the pass finds work that belongs in no issue in its
batch — a gap between two of them, a surface nobody owns — it writes **a register
row**, the one specified in `parallel-hunt/SKILL.md`, carrying an `audience` of
`operator`, `tester` or `agent`, a severity, and `owner-notes` inside 200
characters. Promotion turns the rows that earn it into issues, at the end of the
next run or hunt. A finding is out by default, and promotion is the work that gets
it in.

The seam agent is the likeliest source of these, and the same rule binds it: a seam
finding is a register row, never a new issue file.
