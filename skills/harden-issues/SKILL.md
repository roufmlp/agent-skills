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
| Attack one issue | `harden-issues-attacker` | medium |
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
Fable. The attacker runs at `medium` and the seam at `high`, on the human's ruling of
2026-09-25: the attacker's checklist is enumeration against one file, which is
recall rather than chained reasoning, while the seam reasons across the whole set.

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
every caller: skip any issue whose row in a LIVE run's `run.md` is past
`queued` — in any run, whoever is calling. That is the whole guard. It never
asks which run is live, and it never asks which caller you are. Ticket 33,
ruling 5, ruled by the human 2026-09-07; `decisions.md` holds the blanket rule it
replaced.

**Run the command. Never read a directory.** This is the guard, and there can be
two live ledgers (ticket 38, the one-run-per-feature layout ticket):

```bash
python3 ~/.claude/skills/run-issues/find_live_ledger.py --list
```

It prints `batch id`, `ledger path`, `worktree`, `kind`, tab separated, and it
enumerates EVERY worktree of the repository from whichever one you are standing
in — `git worktree list` is the same list from any tree, measured 2026-09-13 on
a repository whose only live ledger sat in the main checkout.

**Until 2026-09-13 this paragraph said "any `runs/<batch-id>/run.md` in the same
directory", and that sentence caused the fault it exists to prevent.** Run state
is committed, so every worktree carries a copy frozen at the commit it branched
from. In a worktree the same directory is that frozen copy. On 2026-09-13 the
`h0913` pass read its own worktree's `runs/`, could not see run `batch-19ff9f`,
and rewrote issue 37 while that run held it and had committed 720 lines into the
same file; the edit was reverted before the merge. The script was never at
fault and was not changed. The instruction was. Ruled by the human 2026-09-13.

Two consequences, both intended. A run's launch phase sees its own rows at
`queued` and proceeds, because an issue nothing is building yet has no second
writer. And **Run A's launch phase runs while run B is live**, because run B's
rows are not run A's issues.

`needs-harden` and `ready-for-agent` are both in scope — `needs-harden` is what a
run sets when it finds criteria that are wrong or stale, so those issues are
exactly what this pass exists to serve, and a status-shaped guard would tell it to
skip them. **A `parked` issue is in scope only where the human typed it**, and this
pass never adds one to a batch on its own: parked is promotion's floor for a
medium or low row nothing waits on, and
`python3 ~/.claude/skills/lib/sweep_parked.py <issues dir>` is what offers one —
it prints the `/harden-issues` line, `/daily-brief` runs it, and the human chooses.
Hardening is also the way OUT of parked, because the stamp below sets
`ready-for-agent`, so a typed parked issue is hardened like any other. What the guard protects against is a second writer: rewriting criteria
under a working implementer causes a rejection on correct work, then a strike,
then an escalation chasing a criterion the implementer never saw.

**The one exception: strike-2 mode.** A `/run-issues` runner may spawn a single
attacker against an issue it holds, after two rejections, before it buys a third
implementer. The guard above protects against a second writer, and at that moment
there is none — the implementer is dead and the runner spawns nothing else until
the attacker returns. Strike-2 mode is narrower than a normal pass: classes 1, 5
and 9 only, plus class 4's measured population on any guard criterion it
rewrites, evidence or silence, and **it never waits for an answer** — an
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
   reintroduced" — where cheap. A criterion that keeps a message owed until it is
   sent names whom the send must name, so a gate can drive a send to the wrong
   person (`q-fin-c62d38-07`).

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

   **A guard criterion names the population it reads, measured, as a closed
   list.** A guard told to read "the whole artefact" names nothing a build can
   meet, and every adversarial gate plants one more spelling: one tracker's issue 53
   passed every other criterion in all seven attempts and was rejected on a new
   bypass each time. Measure the forms the repository holds today and write three
   lines inside the criterion:

   ```
   Forms: `.ts`, `.tsx` under `src/app/`
   Measured by: `git ls-files 'src/app/**' | sed -n 's/.*\.//p' | sort -u`, <date>
   Outside the list: a form a gate plants that this list does not hold is a register row, not a rejection.
   ```

   The guard still refuses what it cannot place inside that list
   (`~/.claude/coderules.md`, ruled `q-s4-1` on 2026-09-23). A criterion that
   reads like a guard and is not one says so in one line, `Not a guard: <why>`.
   `check_issue_ready.py --all-guards` refuses the stamp on either missing, and
   its docstring holds the measured wording it recognises. (Tracker-tooling
   issue 22, fix F7.)

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

   **A promoted claim you MEASURE FALSE is corrected in place; only a LOOSE one may
   be annotated.** A false sentence at the top of an issue is what an implementer
   reads first, and a correction twelve lines below it arrives too late. So strike
   the false claim where it stands and write the measured truth in its place, with
   the citation; keep the `## Corrections from the hardening pass` section for
   claims that are merely vague or unproven, where the promoted record is still
   worth reading as written. Measured: it happened twice in one batch — issue 407
   opened "The work is lost", false by `new-tender-form.tsx:736-738`, and issue 408
   called the deal board "read-only", false by `sourcing-board.tsx:8`, both with the
   correction sitting below the false line. The pass already writes the correction,
   so this rule only says where it goes. (Ruled by the human 2026-09-18, queue item
   `q-h-078` item 19.)
   **A count the pass writes carries the command that measured it.** Pass
   `h0917c` wrote "twenty-two" colour families into issue 139, and the
   installed Tailwind ships 26. Put the command in backticks in the same
   criterion. A number that is a design choice or a fixture size, not a
   measurement, is quoted on a `Not measured:` line with the reason.
   **An example input and outcome the pass writes carries its command in the
   same clause.** The launch pass of run batch-ce5d7b wrote "`4` finds no bill"
   and "`04 39` returns nothing" into issue 381, and both gates measured both
   false. Measure it, with the command beside it in backticks, or remove it.
   There is no `Not measured:` line for an example. (Ruled by the human 2026-10-07,
   `q-fin-ce5d7b-03`, road A2.)

   **A criterion a run has reset is rewritten, never only added to.** Issue 139c
   gained a broad rule beside the narrow one and kept both: "Both implementers
   built the first. Both gates graded the second." Replace the sentence the run
   found at fault, or strike it with `~~ ~~` where it stands.
   `check_criteria_edit.py` refuses all three faults before the stamp. (Tracker-tooling
   issue 23, fix F9.)
6. **Empty or missing hostile data.** Does QA/production hold data that can
   exercise each criterion? If not, say so and name the fixture to create —
   otherwise the gates validate over an empty set.
7. **Deploy and boundary reality.** Migration ordering (one-way? code-first or
   db-first?), client/server module boundary, platform caps.
8. **Observability.** How will each criterion be verified, and is the property
   observable to a gate or a walk at all? A criterion nobody can observe is not a
   criterion.
9. **Size against the one-implementer bound, which is a COUNT and not a
   duration.** Run the counter; do not estimate minutes:

   ```
   python3 ~/.claude/skills/lib/check_issue_size.py \
     --issues .scratch/<feature>/issues --limit 14 \
     --grade <each issue this pass hardened>
   ```

   **14 is the human's ruling of 2026-09-14**, not a default: no issue may be
   bigger than the biggest one this pipeline has finished. It refuses an issue
   carrying more than `--limit` acceptance criteria, names the count and lists
   every criterion it counted. `--grade` narrows refusal to
   the files this pass hardened, so a backlog minted before the rule is read and
   not refused. A graded file carrying NO criterion also refuses: a count of
   zero is not a pass.

   **Never convert its count into minutes, and never quote a past issue's
   duration as a comparable unless you read it off `issues.jsonl`.** Until
   2026-09-14 this class was a sentence — "a clean issue runs ~30-90 min" — and
   each attacker reasoned by analogy from figures it found in run ledgers. Those
   figures were ESTIMATES that later passes quoted as measurements, so the
   pipeline was calibrating estimates against estimates. The measured record: 25
   issues, median span 36.2 minutes, p90 72, and exactly one over 90. The
   analogy step is where the judgement hid, which is why it is gone.

   The count is the refusal. **The cut is still yours**, and the count does not
   make it for you: suspect anything whose criteria span several independent
   deliverables, or that packs migration plus logic plus UI into one slice, even
   at nine criteria. Propose the cut line — where one half ships and gates alone
   ("extract + harness", then "behavioural tests") — and route it by
   `~/.claude/questionrules.md`'s table: the session settles the split itself
   when it can cut, harden both halves and leave both stampable in this same
   pass; a split it cannot complete that way goes to the human. `/run-issues`
   deliberately never splits mid-run — an oversized issue that reaches a runner
   arrives back here.

   Four candidates attackers have reached for were measured on 2026-09-14 and
   predict nothing: invariant count (rank correlation +0.05), blocker count
   (+0.03), whether the issue ships a migration (+0.25 over a field 19 of the 25
   run issues carried), and whether it touches a browser (+0.13). Do not cite
   one as a size signal.
   `check_issue_size.py`'s docstring holds the whole table and the fit's own
   error bar.

   **The count is scored.** `run_costs.py` writes it onto each issue's line in
   `issues.jsonl` beside the span that issue then occupied, and
   `run_compare.py sizing` reads the two together. The limit is the human's, and
   they re-rule it off that record, never off an attacker's estimate.

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

## Read what the human has already ruled, before anybody attacks the file

An attacker that has not read their rulings asks for them again. That happened in
the last two attended passes — hardening asked for on issues the human had already
cut and ruled — and a question they have answered costs them the same minutes the
second time. Read the project's rulings file and hand it to every attacker with its
issues:

```bash
python3 ~/.claude/skills/lib/rulings.py --list <repo>/.scratch/rulings.md
```

Each entry names the question it answered, the subject, the ruling, and the file
that now carries it. Apply an entry that governs an issue in scope the way you
apply any other fact about the repo, and count it. A project with no rulings
file prints `no ruling on record`, which is the honest state of a tracker nobody
has ruled on yet. An entry the reader cannot parse is named at exit 1 and left
out of the listing: repair that entry before you work from the list, because a
ruling it dropped is one nothing can apply and nothing can refuse.

`~/.claude/skills/lib/check_queue_shard.py` holds the other half at the end of the pass: an item whose
subject matches an entry is refused as **already ruled**, with that entry
printed. Apply it, or say on the item what this asks that the entry does not —
`Rulings checked: none match`, quoting the entry it matched and its nearest
neighbour. An item that names an entry and then contradicts it is a new question
and passes.

## Citations quote text, never a line number

**Every citation you WRITE from 2026-08-26 onward quotes text, never a line
number.**
`src/lib/deals/room.ts`, then the distinctive phrase the line contains, in
backticks. A quoted phrase expires only when the code it names actually changes,
which is exactly when a citation should expire; a line number expires whenever
anything above it grows. Ruled by the human on 2026-08-26 in the daily brief;
`decisions.md` holds what that run broke and the cost they named.

Do not convert the citations already written — 17,345 of them exist across 393
issue files, measured 2026-08-26 — and do not spend a round on it. Repair one in
place as text where you are reading it anyway, so the corpus drains as issues
close.

**There is no separate citation-repair step, and no script to run.** Until
2026-09-15 this section told the pass to run a project's citation checker over
every issue in scope before the attackers spawned, and to correct each `moved`
row. The human deleted that step on 2026-09-15, on a measurement taken in the
`h0915` pass over one tracker: **class 5 already does this work.** Class 5 makes
every attacker verify each factual claim against the real code, and a citation is
a factual claim. In that pass the one drifted citation found — issue 103's
pointer into `src/model/delivery-date.ts` — was found by an attacker reading the
code, not by a script. The script duplicated work the attackers must do anyway
and added a step to every issue in every run.

Two consequences, both intended. A repo that carries such a script does not need
the pass to run it. And a stale citation is now caught as what it always was: a
class 5 unverified premise, reported with the rest.

**This rule alone will not hold, and the human knows it**: a convention nothing
refuses is the remember class their own rules reject. A build check that refuses
the form outright — "nothing refuses a new line number citation in a source
comment" is how the issue that asks for one reads in two of the trackers this pass
came from — is the guard that makes it stick. Where that check has not shipped in
the repo you are hardening, say so in the stamp line rather than adding a sweep
here.

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
- **A claim measured FALSE is corrected in place, never merely annotated.** Strike
  it where it stands, write the measured truth there with its citation, and record
  the change in `## Corrections from the hardening pass`. That section keeps only
  the LOOSE claims — vague or unproven — where the promoted record still reads
  correctly as written. Class 5 carries the measurement behind this rule. (Ruled by
  the human 2026-09-18, queue item `q-h-078` item 19.)
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
- **Both directions, before the stamp.** `## Blocked by` is the section a
  scheduler reads to decide what may be built today, and promotion cannot write
  it: promotion reads a register row and never the code. You read the code, so
  you are the one stage that can. Measured on one tracker on 2026-09-13: not one
  of the 22 needs-harden issues was named as a blocker by any other issue, and
  issue 64, the tab bar, was needed by every screen in prose only. For every
  issue this pass hardened:
  - **Its own section.** Write `## Blocked by` naming every open issue whose
    work it needs, `- None` where nothing does. A file promotion minted carries
    the single bullet `- Unknown until hardened`, which says nobody has looked
    yet; your answer replaces it.
  - **The other direction.** Each attacker's findings file carries a
    `## Downstream edges` section naming the open issues that depend on what its
    issue builds, and `seam.md` carries the ones only the whole set shows. Add a
    bullet naming the hardened issue to each of those issues' `## Blocked by`.
    **Where no seam ran** — a one-issue pass — the attacker's file is the whole
    input, and this half is yours.
  - **Then grade the tracker**, and stamp only on a clean walk:

    ```bash
    python3 ~/.claude/skills/lib/check_issue_links.py --issues <issues dir> \
        --scan <findings dir> --grade <each file this pass wrote>
    ```

    It refuses a stamped issue carrying no section, and an issue whose prose says
    it needs, reads, calls, assumes, builds on or comes after an open issue its
    section does not name — quoting the sentence. **Exit 1 is no stamp**: repair
    what it names, then run it again. **Name every file you wrote in `--grade`,
    and nothing else** — this pass stamps the issues it hardened, and a tracker
    carries issues minted before the rule (128 of one tracker's 641 on
    2026-09-13), so a grade of the whole directory would block every stamp there.
    Ruled by the human 2026-09-13, issue 02 of the tracker-tooling set.
- **Then two refusals over the same files, and stamp only when both exit 0:**

    ```bash
    python3 ~/.claude/skills/run-issues/check_issue_ready.py --all-guards \
        --issue <each file this pass hardened>
    python3 ~/.claude/skills/harden-issues/check_criteria_edit.py \
        --issue <each file this pass hardened>
    ```

    The first refuses a guard criterion with no measured `Forms:` list (class 4).
    The second refuses a count with no command, an example with no command in
    its clause, and an edit that only added to a criterion a run has reset
    (class 5). Run the second before the commit that
    holds the pass's edits, because it compares against `HEAD`; after that
    commit, pass `--base <the commit before it>`.
- Then stamp the issue, one line under `Status:`:
  `Hardened: <date> — <n> sharpened, <m> questions resolved, <r> rulings applied.`
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
than a decision, and stamp — status included, same rule. A default that changes a
criterion is written inside that criterion in one form,
``Default (`q-<pass>-<issue>-<n>`)``, the question's own id, because
`check_issue_ready.py` reads it by that form and no other (issue 43b):

`Hardened (provisional): <date> — <n> sharpened, <m> defaults pending, <r> rulings applied.`

A provisionally stamped issue is in scope for `/run-issues`' own `all`, except a
`Level: full` issue whose criterion carries that mark unruled (rule 7 of issue 32),
and the merge briefing names every one that shipped that way, so the answer arrives after the run
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
than scattered across issue files. The shard states its walk on one line above the
first item: `Walk: none` when it is written, changed to `Walk: <date>` when the human
walks it at the keyboard.
Before the pass finishes, run `python3 ~/.claude/skills/lib/check_queue_shard.py <that
shard>` and stop on exit 1: a heading with no backticked `q-` id is an item the brief can
never retire, and it comes back to the human after they have ruled. Three groups of
queued items were repaired by hand for that fault before the check existed.

**A ruling the human gives at the keyboard goes into the RULINGS FILE, not only into the
issue.** Where an attended pass ends with a ruling, write each one into `.scratch/rulings.md`
as its own entry, with the issue on its `Carried by:` line. An answer recorded only under a
`## RULED ...` heading in the issue is invisible to `check_queue_shard.py`, which grades a
queued question against the rulings file ALONE, so nothing can refuse the re-ask and the next
pass puts the same question again. That happened three days apart on one tracker, and the
human's words were "why this question again?"

**This pack ships no refusal for that, and the gap is deliberate.** A reader who wants one
writes a check that counts the issue files carrying such a heading that no rulings entry
names, and refuses a RISE in that count rather than the count itself — a tracker carries
rulings written before the rule, and a flat refusal would block every stamp on it. The
sibling fault, an entry the reader cannot parse, IS refused at write time, by
`hooks/rulings-write-guard.py` in this pack.

**An accepted default is a ruling too, and the walk closes on a check.** Its entry reads
`Ruled: AS DEFAULTED.`, and its id goes into this tree's `ruled.md` beside every flip,
through `collect_shards.py --kind queue --my-shard --prefix ruled --machinery`. An item the
human waves off carries a `Left for the brief` line in its body. After the walk, and before
the pass's branch merges to main, every item on the shard has an outcome on record — a
flip, an accepted default, or a `Left for the brief` line — and the shard's `Walk:` line
carries a date.

The author's setup refuses the merge otherwise, with `check_walk_closed.py`, which this
pack does not ship; without it the pass holds the rule. That check runs after the walk and
`check_queue_shard.py` before it; in the other order the first refuses every item the walk
ruled. Adopted by the human 2026-10-02, after pass `h1001pk`; `decisions.md` holds the
incident.

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
- **If they are away, or wave the list off**, the default road applies unchanged: take
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
