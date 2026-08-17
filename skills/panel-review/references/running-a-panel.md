# Running a panel

State, output and cost control. Read before the first spawn.

## Where everything lands

`.scratch/panel-review/<date>-<slug>/` — `<date>` is `YYYY-MM-DD`, `<slug>` a few
kebab-case words naming the artefact. Two panels on one artefact in one day need
distinct slugs, or the second run's gate reads the first run's reports and says nothing.

**`panel.md`, written before the first spawn.** The run's **ledger**: tier and its
reason, the artefact paths and step 1's target line, the failure-mode table, the frozen
corpus, the invariants, and one row per persona carrying its status, its report path and
**the full lens text as spawned**. Tables only, no narrative, because every spawn reads
it.

Two jobs. It makes the run resumable: a session handed this directory re-spawns the rows
marked neither `returned` nor `failed`, each with the lens that row records — which is
why the lens lives here and not only in a spawn prompt the dead session was holding.
And it keeps the corpus frozen — a persona re-spawned tomorrow that derives its own
cases walks different inputs, so two personas would then disagree because they
imagined different scenarios, reported as a real conflict. The disagreement map is
the synthesis engine, and it only carries signal when every persona walked the
identical case.

**A scenario carrying a number launders it.** Write "a long report" and each persona
reasons from its own sense of long; write "a 400-line report" and all of them are
entitled to a figure nobody measured. The no-guessed-numbers rule binds whoever writes
the corpus, not just the personas reading it.

**One file per persona**, at the path each spawn is given. Personas write their full
report there and return only a stub, so this session stays able to synthesise. A persona
reads `panel.md` and nothing else in the directory: the other reports and the
orchestrator's own notes sit there too, and one glance at either turns independent
agreement into an echo.

**Findings are addressable, and this session opens the verdict file.** Persona *n*
numbers its issues `p<n>-1`, `p<n>-2`. Before the gate spawns, write `gate.md` with one
row per finding id and one per invariant, every verdict cell reading `pending`:

```
| id | verdict | why |
|---|---|---|
| p3-1 | pending | |
| inv-2 | pending | |
```

A finding's verdict is `confirmed` or `retracted`; an invariant's is `HOLDS`, `GAP` or
`UNTESTABLE BY READING`. The gate edits its own rows and creates nothing.

The skeleton exists because a gate that dies writes nothing. Two did, at the weekly
usage limit, in one day, and both times someone had to dig the mechanical citation
checks out of a transcript by hand. Rows the gate never reached stay `pending`, so a
dead gate now leaves a partial verdict and a list of what is owed.

Nothing else in the directory is edited — a status written into a persona report
destroys the on-disk state a resumed run reads.

**`report.md`**, below.

The tier sets the **deliverable**, not the state: `quick` gives a verdict in the chat,
`standard` writes `report.md`, `deep` adds `gate.md`. Every tier writes `panel.md` and
the persona files, because a spawn needs somewhere to write and a resumed run needs a
ledger.

## The report: seven sections, fixed

Any of them may say "none". Seven that may be empty beat a longer list where each must
say something, which is how a report template turns into filler.

1. **Verdict.** Opens with one provenance line: tier, persona count, whether a gate
   ran, how many findings it retracted, how many rows it left `pending`, and any
   persona that `failed`. The report a reader sees most often is the ungated one, and
   nothing else in it says so. A part-gated report is the same hazard wearing a gate's
   clothes, so the pending count goes in the same line.
2. **Invariants.** Each one `HOLDS` with its citation, `GAP` with the nearest
   insufficient mechanism and why it falls short, or `UNTESTABLE BY READING`.
3. **Agreed findings, ranked.** What three or more personas raised independently, each
   naming the personas and the scenario behind its count. The provenance is already in
   `panel.md`; a bare count is a number nobody can check.
4. **Disagreement map.** Each one decided, with the reason stated. Never resolved by
   inventing a fact; unresolved is a legitimate outcome. **Retracted** findings land
   here too, each with the gate's reason.
5. **The deliverable.** Opens with the personas' must-survive statements, merged — the
   only grounds for *preservation* this format collects. Then the deliverable itself:
   final draft for prose, `file:line → change` for a design, a recommendation and its
   reason for a decision. In the prose branch every difference from the original traces
   to a confirmed finding; anything else is not in the draft.
6. **Experiments to run.** Every `UNTESTABLE BY READING`, plus every finding that
   needed a number this pass refused to estimate.
7. **Scenarios omitted.** What the cap dropped, so the gap is visible.

Unresolved forks append to `.scratch/decisions-queue.md`, so they reach the human in a
single list via `daily-brief` rather than sitting in a report they have to remember
to reopen.

## Cost

`deep` is seven to nine spawns.

**The caps are on counts, not on width.** Five issues maximum per persona, one verdict
line per section, invariant marks, must-survive list — slot counts rather than an
instruction, because a rule asking a busy agent to be brief is a rule that fails. What
no slot count reaches is length: nothing bounds how long a report runs, so fan-in is the
cost this format does not control.

**Pre-flight, one line, before any spawn:** tier, persona count, scenario count, gate,
output path.

**`deep` waits for the human. `quick` and `standard` print and proceed.** The spend is all
in `deep`, and a confirmation on the common path gets clicked through until it stops
working as a control anywhere.

Never two stops in one invocation. Where this pass also had to write a brief, the
brief and the pre-flight go in one message and it waits once.

With no human present — a scheduled or background run — `deep` proceeds, and the
report records that the pre-flight was auto-approved with nobody there. Blocking
forever is useless and silently downgrading is worse: overspending is recoverable, a
shallow review of an irreversible artefact is the failure this pass exists to prevent.

**The cost log.** One line per run appended to `.scratch/panel-review/cost-log.md`:

```
date | artefact | tier | spawns | session model | found anything new?
```

No wall-clock column: nothing in this pass captures it, and a duration timed by hand is
not comparable with the next one. The last column is the orchestrator's own judgement on
the run it just paid for, so read the log as a series rather than a verdict, and read
`report.md`'s experiments section for what would actually settle whether a tier earns
its spawns.
