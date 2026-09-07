---
name: harden-issues
description: Attack acceptance criteria at authoring time — a blind-spot pass over issue files that sharpens criteria with evidence, names invariants, and routes open forks to the human. EXPLICIT INVOCATION ONLY. Use this skill only when the user types the command /harden-issues, or when the /to-issues skill calls it on freshly drafted slices. Never infer it from wording such as "harden these issues", "pre-batch pass" or "attack the criteria".
argument-hint: "a named batch — issue numbers or a range — or nothing when invoked by /to-issues on drafts"
---

# Harden issues

Attack acceptance criteria before anyone builds to them. An issue whose criteria
are wrong when written passes every gate — the implementer builds to the bad spec
and both gates grade against that same bad spec. This pass is the early fix.
It is also what buys the next run an uninterrupted one: anything the run would
otherwise stop and ask a human for is settled here, while a human is at the
keyboard (see "Checks only the human can run"). Provenance and the incident record
live in this directory's `decisions.md`; read it when changing this skill, not
when running it.

Three entry points, same pass:

- **From `/to-issues`** — runs on the drafted slices before the user quiz; the
  pass's questions join that quiz.
- **Inside a run's launch** — a `/run-issues` launch whose scope holds a typed
  issue with no `Hardened:` line reads `run-issues/launch-harden.md`, and that
  file drives this pass over those issues before its first implementer spawns.
  It settles what it can, drops what it cannot, and commits the hardened files
  before spawn 1. Findings go to that run's own directory, not the shared one
  (see below). Ticket 33 of the pilot-delivery map, ruling 16, ruled by the human
  2026-09-07.
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
citation into current code (the file plus its distinctive quoted phrase — the
2026-08-26 form), a query against real data, or a measured value. The
same bar the run gates use. Everything else — and **every open fork** — becomes a
numbered question for the human. The pass never settles a fork by choice.

Any road-shaped statement it writes ("the rule is X", "the cause is Y") is a
hypothesis unless its premise was tested. Untested → write it as a hypothesis
with an explicit premise-check clause for the implementer, testing the premise
itself, not a narrow question near it.

## Fan-out

**A prohibition in a brief names the SYSTEM, not the verb.** Every "do not" carries the
forbidden thing AND the permitted one, with an absolute path wherever a path exists. A brief
that constrains the ACT while leaving the PLACE unnamed gets a different answer from every
agent. Adopted by the human, 2026-08-09; `run-issues/decisions.md` holds the three faults it
was adopted on.

Each role is a registered agent type carrying its own brief, model and effort.
Spawn by `subagent_type`; the pass never pastes a brief.

| Stage | Agent type | Effort |
|---|---|---|
| Attack one issue | `harden-issues-attacker` | high |
| Seam pass over the set, once | `harden-issues-seam` | high |

Attackers run concurrently, one per issue. The seam agent runs after them all,
reading every issue plus the attackers' findings files. **It is skipped where
only ONE issue was attacked**: gaps between issues need two, and a batch of
fifteen holding one unstamped issue would otherwise buy a pass over fifteen
files to find them around it. A run's launch reaches this through
`run-issues/launch-harden.md`, which states the same condition at the point it
spawns.

Findings go to files, not through this session's context: attackers write
`.scratch/<feature>/harden/<issue>.md`, the seam agent writes
`.scratch/<feature>/harden/seam.md`. The pass reads counts, questions and each
findings file's `## Checks for the human` section, never the working.

**A run's findings go to `runs/<batch-id>/harden/` instead**, beside that run's
own ledger: `.scratch/<feature>/runs/<batch-id>/harden/<issue>.md` and
`.../harden/seam.md`. That is both callers inside a run — the launch phase and
strike-2 mode. The attended pass keeps the shared directory. Ticket 33 of the
pilot-delivery map, ruling 7, ruled by the human 2026-09-07.

**On each attacker return, check the file exists and holds something — before
the seam agent spawns, and before anything is stamped:**

```bash
python3 ~/.claude/skills/lib/check_verdict.py --file .scratch/<feature>/harden/<issue>.md
```

Inside a run, that path is `.scratch/<feature>/runs/<batch-id>/harden/<issue>.md`.

A non-zero exit means that attacker produced nothing, whatever its final message
said, so the issue was not hardened. Re-spawn it, or leave the issue unstamped
and name it as unattacked. **An issue nobody attacked is never stamped
`ready-for-agent`**: the stamp is what puts it in the next run's scope, so a
silent gap here ships exactly the bad spec this pass exists to catch. A missing
file also narrows the seam agent's input without saying so.
`run-issues/decisions.md` holds the two gates that died silently and made this a
check rather than a reminder.

**Model: inherit.** Both agent files carry `model: inherit`, so the pass runs on
the tier the session was launched on. To harden on Fable, launch the session on
Fable. Effort stays `high`, not `max`: the checklist is enumeration against a
file, and enumeration is recall rather than chained reasoning.

**Print one launch line before spawn #1, on every invocation** — the resolved
session model, the issues in scope, and how many attackers are about to spawn.
Not a wait, an interrupt window — do not ask, and do not stall for an answer.

**Whether a spawn carries a `model:` value depends on which caller you are, and
there is a hook on both roads.** An attended pass passes none: the Agent tool's
`model` parameter beats agent-file frontmatter, so a spawn-time value defeats
`inherit` silently and nothing downstream records which tier ran. The launch
line is the one place a wrong tier is visible, and the stamp does not carry it.
**A pass inside a run does the opposite: carry the ledger's value for the role
on every spawn**, `attacker` or `seam`, read off that run's `Model map at
launch:` header line. **This pack ships no refusal for that**, so the value is a
rule the pass holds; `hooks/README.md` says what a reader gains by writing one.
Ticket 33, ruling 2.

**Never attack an issue a live run holds.** One rule, and it reads the same for
every caller: skip any issue whose row in any `runs/<batch-id>/run.md` in the
same directory is past `queued` — in any run, whoever is calling.
`find_live_ledger.py --list` prints the live ledgers, and there can be two
(ticket 38, the one-run-per-feature layout ticket). That is the whole guard. It
never asks which run is live, and it never asks which caller you are. Ticket 33,
ruling 5, ruled by the human 2026-09-07; `decisions.md` holds the blanket rule it
replaced.

Two consequences, both intended. A run's launch phase sees its own rows at
`queued` and proceeds, because an issue nothing is building yet has no second
writer. And **Run A's launch phase runs while run B is live**, because run B's
rows are not run A's issues.

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
unsettled reversible fork takes its recommended default by the routing table,
and only a fork in the table's four `[irreversible]` classes, or a split,
returns as a blocked issue, not a question the run sits on.

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
   rule bites today. (Adopted by the human 2026-08-07, from the 238-245 finale; three
   implementers warned about this class avoided it three for three.)

   **A criterion that moves security-relevant code pins the property, not the
   count of surviving tests.** The surviving tests are one more list of instances,
   and "the existing tests keep passing" grades the move against that list rather
   than against the rule the moved code holds. Name the property the code must
   still hold — "a caller-supplied needle deletes only what it literally matches" —
   and name a hostile input and an over-long input the criterion covers. (Adopted
   by the human 2026-08-18 as R1, from the `cab74e` run; `decisions.md` holds the
   incident.)
4. **Guards that cannot fail.** Each criterion states how a violation would be
   observed. Prefer mutation-shaped criteria — "reds when X is deliberately
   reintroduced" — where cheap.

   **A criterion that names a mutation must have that mutation driven once
   before the issue ships.** Not described, driven: make the change, watch the
   test red, put it back, watch it green. An undriven mutation is a guard nobody
   has proved can fail, which is the class this whole entry exists to close.
   (Adopted by the human 2026-08-07, from the 247-170 run.)

   **Grade the drill, not only the criterion. A drill must name the red it
   produces AND a wrong reason it could go red.** Where a criterion carries a
   mutation or a drill, refuse it here unless it answers both. A drill that only
   states "this reds when the guard is removed" is compatible with a guard that
   tests nothing, because a drill inherits its author's model of the system: if
   the author is wrong about what the code receives, the fixture is wrong the same
   way and the two agree with each other while agreeing with nothing real. Naming
   the wrong-reason road is what separates a drill that proves a property from one
   that proves an author is self-consistent.

   This is an authoring-time refusal and it costs no run time. Do not answer this
   class by asking an implementer to check their own drill harder — that is the
   reminder that already failed. (Adopted by the human 2026-08-19, from the `e047ba`
   finale, queue item D4; `decisions.md` holds the ten green guards and the
   refusal of mutation testing as the mechanical alternative.)

   **A criterion may never ask for evidence to land somewhere the party it names
   cannot write.** Read the clause, name its writer, and check that writer's
   pen. Two homes fail today: an implementer writes neither the issue file nor
   the commit message. Send the evidence to a test, a doc comment, the register
   or the merge briefing — all four survive a run's own write rules. Where the
   evidence genuinely belongs in one of the closed homes, address the clause to
   the party that holds that pen, which for a commit message is the runner and
   for a verdict is the gate.

   The check is mechanical, because the clause names its own writer. Refuse it
   here, at authoring time. (Adopted by the human 2026-08-10 for the issue file,
   **widened by them 2026-08-16 to any closed home**; `decisions.md` holds both
   incidents.)

   **A constraint taken from measured data is labelled as one.** Where a criterion
   or an invariant fixes a number because that is what today's input holds, write
   it into `## Must still be true` as an assumption a later issue may need to
   lift, and say the migration header must do the same. (Adopted by the human
   2026-08-10, from the 301-307 finale. The run-issues copy carries the incident.)
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
   by the human 2026-08-07. This edits class 5 deliberately and must never become a
   class of its own — two homes for impossibility claims is the drift it avoids.)
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
   and route it by `~/.claude/questionrules.md`'s table: the session settles
   the split itself when it can cut, harden both halves and leave both
   stampable in this same pass; a split it cannot complete that way goes to
   the human. `/run-issues` deliberately never splits mid-run — an oversized
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
    file as a numbered action and `## Target database` records the intent. Same
    reason as class 4's rule on evidence in the issue file: an agent cannot meet a
    criterion aimed at somebody else.

    Unanswered, this defaults: the writable database during the run, then the
    production database, owner the human, after the deploy — written as a default.
    Silence is what this class exists to catch, so a pending action nobody needed
    is the cheap error. (Adopted by the human 2026-08-12, from the 301-307 run:
    `decisions.md`.)

11. **Joint satisfiability.** For each criterion, one real input on which it can
    pass; for each pair of criteria sharing a surface, one artefact satisfying
    both. A criterion with no satisfying input, or a pair that cannot both hold,
    is refused at authoring time. Attack this hardest on a freshly cut issue — a
    cut strands criteria written against the whole. (Adopted by the human 2026-08-29,
    from the ticket 33 audit; `decisions.md` holds the five criteria resets it
    was measured on.)

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

**Every citation you WRITE from 2026-08-26 onward quotes text, never a line
number.** `src/lib/deals/room.ts`, then the distinctive phrase the line contains,
in backticks. A quoted phrase expires only when the code it names actually
changes, which is exactly when a citation should expire; a line number expires
whenever anything above it grows. Do not convert the citations already written —
17,345 of them exist across 393 issue files, measured 2026-08-26 — and do not
spend a round on it. Repair a `moved` row in place as text, so the corpus drains
as issues close.

Ruled by the human on 2026-08-26 in the daily brief; `decisions.md` holds what
that run broke and the cost they named. **This rule alone will not hold, and they
know it**: a
convention nothing refuses is the remember class their own rules reject. Issue 406,
"nothing refuses a new line number citation in a source comment", is the guard
that makes it stick.

**This pass is where the repair happens, by the human's ruling of 2026-08-15.** A run
may not write an issue file, so `/run-issues` reports these and leaves them; the
347/263 run left eight. You already read the whole file and you are already
allowed to write it, so the fix costs nothing extra here and costs a round
everywhere else. A `holds` is not proof: the check compares against the commit
that last touched the citation's own line, so a citation rewritten without
re-checking its number can read `holds` and still be wrong.

## Output and the stamp

- Evidence-backed sharpenings are edited into `## Acceptance criteria` and
  `## Must still be true` directly, each carrying its citation.
- **The `Sentence:` header line may be rewritten in place.** A missing or
  over-long one is a finding the pass fixes without asking anybody, because the
  title it compresses is already written and the fix is a transcription. The rule
  is a subject and a verb, present tense, `59 characters or fewer`. This is the
  one header line the pass owns: `Status:` and `Hardened:` stay with the
  orchestrating session, and an issue file carrying no such line is legal and
  gets one written rather than a refusal.
- **Say how many citations were repaired** in the stamp line below, so a reader
  can tell a quiet pass from one that found nothing.
- **Every question follows `~/.claude/questionrules.md`.** That file sets the two
  tiers and the parts each carries. A question with no default is a question the
  pass has not finished thinking about.
- **An `[irreversible]` mark must carry the measurement that establishes its blast
  radius, or the mark is refused at authoring time** and the question takes a
  recorded default like any other. The mark is what exempts a question from
  defaulting, so an unmeasured mark buys an unattended stall on nobody's evidence.
  (Adopted by the human 2026-08-29, on the ticket 33 audit; `decisions.md` holds
  the incident. `questionrules.md` reserves the mark for four classes, and its
  routing table says which; a question outside those four classes never takes
  the mark at all.)
- Questions go to the human: into the `/to-issues` quiz, or as the standalone numbered
  list. Apply their answers to the files.
- Then stamp the issue, one line under `Status:`:
  `Hardened: <date> — <n> sharpened, <m> questions resolved.`
- **Stamping also sets `Status: ready-for-agent`.** The two must agree, and the
  stamp alone is not enough: `/run-issues` resolves `all` from the `Status:`
  line and skips anything reading `needs-*`, so an issue that entered through
  the standalone door and keeps its `needs-harden` status is silently dropped
  from the next batch while this pass reports it ready. Keep any minting or
  provenance note on its own `Provenance:` line, never as a suffix on `Status:`.

**A recorded default that governs graded behaviour blocks the stamp until its rule
has a graded home.** Before stamping, walk the defaults this pass is carrying. For
each one, either write its rule into `## Acceptance criteria` or `## Must still be
true`, or state in the file why that default grades nothing. **A default with
neither is an unstamped issue**, and this is a refusal rather than a reminder: it
is the last thing checked before the stamp is written.

This is not a text search. Whether a default names graded behaviour is a reading
judgement, and a search would either miss it or fire on every question. The pass
already enumerates its defaults, so this adds a column to work it does anyway, and
it leaves a record a later reader can audit: for each default, where its rule lives.

Adopted by the human 2026-08-28, after run `99b-99e-6e11ba`; `decisions.md` holds
the measurement it was adopted on.

**An open question never removes an issue from a run.** Where the human has not
answered, take the recommended default, write it into the file as a default rather
than a decision, and stamp — status included, same rule:

`Hardened (provisional): <date> — <n> sharpened, <m> defaults pending.`

A provisionally stamped issue is in scope for `/run-issues`' own `all`, and the merge
briefing names every one that shipped that way, so the answer arrives after the run
instead of holding it up. An `[irreversible]` question is not defaultable — it
leaves the issue unstamped, and out of that scope until the human rules. A split
follows the routing table in `~/.claude/questionrules.md`: the session completes
it — cut, harden both halves, stamp both — and records it; a split the session
cannot complete leaves the issue unstamped until the human rules. This pass has no
`all` of its own; it takes the batch it was given.

Every defaulted question is also appended to this pass's own queue shard —
`collect_shards.py --kind queue --my-shard --prefix <pass id>`, with an id on
each item's heading, because `decisions-queue.md` is generated and refuses a
direct write. The queue is the one place `/to-prd`, `/to-issues`, `/triage` and
this pass all queue decisions, so they reach the human in a single list rather
than scattered across issue files.

Where an answer needs input nobody here has — a third party, a credential, a
product call with no defensible default — set `needs-harden` instead, so the issue
comes back to this pass rather than dying in a status nothing reads.

`/run-issues` lists unstamped scoped issues in its launch message — a launch-time
line for the human, never a gate, never mid-run.

## Checks only the human can run happen here, not mid-run

A criterion that waits on a value only the human can fetch — a row in the production
database, a setting in a provider console, anything behind a credential the agents
do not hold — costs the run an unattended stall if it survives this pass. The
hardening session is attended. Settle it here.

- **Collect them as you attack.** An attacker that cannot verify a premise because
  the check is out of its reach records a check, not a question: what to run or look
  at, where, and which criterion in which issue the answer decides. Both agent types
  write them under `## Checks for the human` in their findings file, which is where this
  session reads them.
- **Run everything you can run yourself first.** QA is writable, the code is
  readable, most premises need nobody. The list the human sees carries only what the
  repo's rules or the credentials put out of your hands, and each item says in one
  clause why it is theirs.
- **Every item carries its failed attempt.** The command that was run and what it
  returned, or the wall — the credential or console — that stops any command from
  reaching the value. An item carrying neither is not a check: the pass runs it
  itself or deletes it, and it never reaches them.
- **A defaulted question kills the checks that only serve it.** Before the list
  goes to them, walk it against the defaults this pass recorded: a check that
  exists only to decide a question already defaulted dies with the question, and
  survives only where it also decides something else — then the item says what.
  Each check names the criterion or question it decides, so this is a read of two
  lists. (Both adopted 2026-08-29; incidents in `decisions.md`.)
- **Put the list to them at the end of the pass, in the same session as the
  questions.** Numbered, one action per item, and for any provider console the
  current official button names, per the pending-actions rule in
  `~/.claude/CLAUDE.md`.
- **Write their results into the issue files as facts**, cited `checked by the human
  <date>` with the query or the setting quoted. That citation meets the
  write-authority bar the same way a file:line does.
- **A check that can overturn an issue's premise must be answered BEFORE that issue
  is stamped, not after.** Sort each check as you write it: does its answer decide a
  criterion, or the issue's premise? A premise check leaves its issue unstamped until
  they answer — it is not defaultable, whatever tier the question carries. Adopted by
  the human 2026-09-07, on issue 465: an attacker, the seam pass and the orchestrating
  session all read the code correctly and still got the issue wrong, because the one
  datum that settled it — the text of the auto-reply — was on their phone. The pass
  routed the check to them correctly and then stamped the issue anyway; their answer
  arrived and unstamped it.
- **No hardened issue may ask the run to stop for a human.** A criterion that tells
  the implementer to run a script and report the output, or to pause for a value, is
  a defect in the issue. Either the check happens here and the answer goes into the
  file, or the criterion is rewritten so the implementer and the gates settle it
  alone.
- **If they are away, or waves the list off**, the default road applies unchanged: take
  the default, write it as a default, queue it to this pass's queue shard. A
  check nobody ran never holds the batch.

## Scope notes

Issue trackers are per-project (this repo: `.scratch/<feature>/issues/`). The pass
edits issue files only — never code, never the tracker board, never another
skill's state.

**The pass never mints.** It sharpens the issues it was given and creates none.
A split it completes keeps the parent's number with a letter suffix (`216b`), which
needs no claim; a genuinely new file, which this pass does not write, takes its
number from `python3 ~/.claude/skills/lib/claim_number.py issue <dir> --for <who>`, and
`number-claim-guard.py` refuses an unclaimed one (ticket 38, rulings 7 and 16).
`decisions.md` holds the pass that ran ahead of this rule. Where the pass finds
work that belongs in no issue in its batch — a gap between two of them, a surface
nobody owns — it writes **a register row**, the one specified in
`parallel-hunt/SKILL.md`, into its own register shard (`collect_shards.py --kind
register --my-shard --prefix <yours>`; the generated `register.md` refuses a write),
carrying an `audience` of
`operator`, `tester` or `agent`, a severity, and `owner-notes` inside 200
characters. Promotion turns the rows that earn it into issues, at the end of the
next run or hunt. A finding is out by default, and promotion is the work that gets
it in.

The seam agent is the likeliest source of these, and the same rule binds it: a seam
finding is a register row, never a new issue file.
