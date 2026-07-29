# agent-skills

Skills, steering rules and multi-agent workflows I use with Claude Code, published
as I write them. The interesting part is orchestration: an autonomous issue runner
and a parallel bug hunt that spawn fresh subagents for every job, gate their output
adversarially, and resume themselves across rate limits. Everything here runs my
real projects first; this repo is the record.

## How the pieces fit

Three layers. Steering documents set standing rules for every session. Skills
encode workflows a session can invoke. The orchestration skills go further: they
turn one session into a thin runner that spawns workers and gates as disposable
subagents, with all state in files so any later session can resume the run.

```mermaid
flowchart TD
    ST["steering/ — CLAUDE.md, writingrules, coderules<br/>standing rules for every session"] --> SES["a Claude Code session"]
    SES -->|invokes| SK["skills/ — repeatable workflows"]
    SK --> HI["harden-issues<br/>criteria attack pass"]
    SK --> RI["run-issues<br/>autonomous issue runner"]
    SK --> PH["parallel-hunt<br/>concurrent bug hunt"]
    HI -->|stamps issues for| RI
    RI --> W1["fresh implementer per issue,<br/>adversarial verify + review gates"]
    PH --> W2["finder and fixer workers,<br/>adversarial claim + fix gates"]
    W1 --> F["state lives in files, not contexts —<br/>any session can resume the run"]
    W2 --> F
    HI -.->|queued questions| DB["daily-brief<br/>one list, once a day"]
    RI -.->|queued questions| DB

    classDef rule fill:#eef2f6,stroke:#64748b,color:#0f172a
    classDef skill fill:#dbeafe,stroke:#2563eb,color:#0c1e3a
    classDef worker fill:#fef3c7,stroke:#d97706,color:#3f2d02
    classDef state fill:#dcfce7,stroke:#16a34a,color:#052e16
    class ST,SES rule
    class SK,HI,RI,PH,DB skill
    class W1,W2 worker
    class F state
```

## The orchestration skills

### [run-issues](skills/run-issues/SKILL.md)

One thin runner session implements a range of tracker issues end to end,
unsupervised. The human is needed once: the merge read at the end.

```mermaid
flowchart TD
    N["next issue from the ledger"] --> IMP["fresh implementer subagent<br/>tests first, one issue, then dies"]
    IMP --> VG{"verify gate<br/>drives the running app"}
    VG -->|rejects with observed behaviour| STRIKE
    VG -->|passes| RG{"review gate<br/>tries to refute the diff"}
    RG -->|rejects| STRIKE["strike recorded"]
    RG -->|passes| C["commit · ledger updated"]
    STRIKE --> Q{"second strike?"}
    Q -->|"no — retry"| IMP
    Q -->|"yes — dismiss"| ESC["escalated implementer<br/>stronger model, both verdicts,<br/>none of the failed reasoning"]
    ESC --> VG
    C --> MORE{"issues left?"}
    MORE -->|yes| N
    MORE -->|no| FIN["coherence finale<br/>reads the branch as one change"]
    FIN --> H["human merge gate<br/>nothing merges without it"]

    classDef work fill:#fef3c7,stroke:#d97706,color:#3f2d02
    classDef gate fill:#fee2e2,stroke:#dc2626,color:#4c0519
    classDef state fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef human fill:#dbeafe,stroke:#2563eb,color:#0c1e3a
    class N,IMP,ESC,STRIKE work
    class VG,RG,Q,MORE,FIN gate
    class C state
    class H human
```

The design choices that earn their keep:

- Every worker is a fresh subagent. An implementer gets one issue; verify and
  review gates get one verdict each, then die. Context never accumulates, and a
  codebase primer means exploration is paid once per run, not once per issue.
- Gates are adversarial and must cite driven evidence. A verify gate drives the
  running app and rejects with observed behaviour; a review gate tries to refute
  the diff. "It looks right" is not a verdict.
- Two strikes and the implementer is dismissed. A fresh implementer on a stronger
  model gets the issue and both rejection verdicts, but none of the failed
  reasoning, and is told not to trust the previous diagnosis.
- The ledger is thin because every spawn reads it; the narrative lives in a
  journal only a resuming runner and the finale read. Shared external quotas
  (API caps, send limits) are run state owned by the runner, and one agent holds
  the spend window at a time.
- A halt writes its own resume state into the ledger — what is on disk, what is
  owed, in what order — so a run picks up where it stopped whether a session cron
  revives it or a human does. Nothing merges without a human.

### [harden-issues](skills/harden-issues/SKILL.md)

The fix for the failure mode gates cannot catch: an issue whose acceptance
criteria were wrong when written passes every gate, because every gate grades
against the issue. This pass attacks criteria at authoring time — one attacker
subagent per issue plus a seam agent over the whole set, working a checklist of
nine blind-spot classes that each shipped a real defect through green gates
(unstated invariants, vague words, guards that cannot fail, unverified premises,
empty test data, deploy ordering, unobservable criteria, oversized slices, plus
a seam pass for what falls between issues). It may only write what it can cite
evidence for; every open fork routes to the human. Hardened issues carry a dated
stamp that `run-issues` checks at launch.

### [daily-brief](skills/daily-brief/SKILL.md)

The human loop, made single. Nothing in the chain stops mid-run to ask a
question — every skill takes its recommended default, records it as a default
rather than a decision, and queues it. This skill collates those queues, plus
unmerged branches and anything else resting on a human, into one brief read once
a day, then writes the answers back. Merge approvals carry the branch SHA they
were read against: a branch that moved since is re-presented, never merged — a
stale approval is not an approval.

### [parallel-hunt](skills/parallel-hunt/SKILL.md)

A concurrent bug-hunt round: finder and fixer workers run as background subagents
over a shared file register, with claim gates killing phantom bugs before they
enter the pipeline and fix gates refusing fixes that mask symptoms.

```mermaid
flowchart TD
    REG[("the register<br/>one file · the only handoff")]

    FIND["finder subagent<br/>may only add regression tests"] --> CG{"claim gate<br/>tries to refute the bug"}
    CG -->|retracted| DEAD["phantom killed<br/>before it costs a fix"]
    CG -->|promoted| REG

    REG --> FIX["fixer subagent<br/>owns shipped code · test-first"]
    FIX --> FG{"fix gate<br/>tries to refute the fix"}
    FG -->|"sent back — masks a symptom"| FIX
    FG -->|verified| DONE["entry closed"]
    DONE --> REG

    FIND -.->|"one work unit, then replaced"| FIND
    FIX -.->|"one work unit, then replaced"| FIX

    classDef work fill:#fef3c7,stroke:#d97706,color:#3f2d02
    classDef gate fill:#fee2e2,stroke:#dc2626,color:#4c0519
    classDef state fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef dead fill:#eef2f6,stroke:#64748b,color:#0f172a
    class FIND,FIX work
    class CG,FG gate
    class REG,DONE state
    class DEAD dead
```

Nobody waits on anybody: the finder is hunting the next bug while the fixer is
still on the last one. Strict code ownership is what keeps the merge tax at zero
while they run concurrently — the finder may only add regression tests, the fixer
owns shipped code. Workers are replaced after each work unit because long sessions
degrade quietly, and because the register holds everything, succession needs no
handover.

## The other skills

### [designrules](skills/designrules/SKILL.md)

Taste, made loadable. A distilled set of design rules (hierarchy, spacing,
typography, colour, states, the premium-feel psychology) that agents must read
before any visual work. It exists because "make it look good" is not an
instruction; a checklist an agent can be held to is.

### [panel-review](skills/panel-review/SKILL.md)

The orchestration idea pointed at prose. One reviewer has blind spots, so this
spawns four to six personas as parallel subagents — each gets the draft, the
target and its own brief, never another persona's output — then synthesises on
agreement, maps the disagreements and decides each with a stated reason. The
mechanism is borrowed from Stanford's STORM (OVAL Lab, NAACL 2024), whose panel
researches topics; here the panel is picked per artefact instead. The rule that
makes it safe on career copy: personas advise on selection and framing only, and
one suggesting a fabricated number is overruled in synthesis, not obeyed.

### [memory-reel](skills/memory-reel/SKILL.md)

A different genre: turns a folder of mixed photos and videos into an edited,
music-driven film, unattended. Inventory and contact sheets before any questions,
a plan the user approves before any build, and chunked resumable scripts because
sandbox shells die mid-render. First version; actively improving.

## Steering

[steering/](steering/) holds the standing rules every session loads: a lean
global [CLAUDE.md](steering/CLAUDE.md) (context hygiene, when skills are
mandatory, how to brief me on manual steps),
[writingrules.md](steering/writingrules.md) (how to write like a person, distilled
partly from Wikipedia's "Signs of AI writing" catalogue) and
[coderules.md](steering/coderules.md) (security non-negotiables grounded in the
OWASP Top 10 and the Supabase production checklist, plus a pre-launch gate that
runs every time). These are the difference between an agent that works for me and
an agent that works.

## The agent definitions

The orchestration skills don't paste briefs into their workers. Each role is a
registered agent type in [`agents/`](agents/), and the runner spawns it by name.
An agent file carries its own brief, model and effort level, and is loaded only
when that role actually runs — so the skill stays a thin protocol and the detail
lives with the role that needs it.

Thirteen roles: six for `run-issues` (implementer, escalated implementer, verify
gate, review gate, a critical review gate for diffs that change money or auth, and
the coherence finale), five for `parallel-hunt` (finder, fixer, claim gate, fix
gate, and a critical fix gate) and two for `harden-issues` (the per-issue attacker
and the cross-issue seam agent).

This is also the only way to set effort per role — the `Agent` tool takes a model
but no effort parameter, so without these files every worker silently inherits one
session-wide setting. [How the models and effort levels were
chosen](docs/model-and-effort-choices.md), including what the measurements said and
where they contradicted the documentation.

## Case study

[Five issues, one unsupervised day](docs/case-study-five-issue-run.md) — a real
run of `run-issues` on a multi-tenant SaaS build: 139 tests added, zero
regressions, two adversarial rejections that were both genuine money defects, a
two-strike escalation that beat symptom-patching with a type-level redesign, and
the post-run review that fed eight revisions back into the skill you see here.

## Using these yourself

Copy any skill folder into `~/.claude/skills/` and it becomes invocable in Claude
Code. The orchestration skills assume issues living as files (this pack's
convention: `.scratch/<feature>/issues/`, a `Status:` line first) and a repo with
tests worth gating on; the steering docs are mine — take the structure, replace
the taste.

**The orchestration skills also need the agent definitions.** Copy `agents/`
into `~/.claude/agents/` — the runner spawns roles by name, so without them a run
stops at the first spawn with "agent type not found". Two things to know: newly
copied types can take a moment to appear, so restart Claude Code only if a spawn
still reports the type missing; and an invalid `effort:` value is accepted
silently and falls back to the default, so a typo costs you the setting with no
warning.

The files use `model: inherit`, meaning every worker runs whatever model the
session runs. Start the session on the model you want the run to use.

**Nothing here needs editing before it runs.** The skills and agent files depend
on each other and on nothing outside this repo — no personal memory files, no
project-local skills, no named model. Where a run wants something a project may or
may not have (a preview deploy, a canonical env file, a skill that drives the
running app), it is written as a conditional and the run works either way. The
steering docs are the exception, and deliberately so: they are my taste, published
to be replaced rather than adopted.

## Credits

My daily process skills (`tdd`, `grilling`, `to-issues`, `handoff`, `triage` and
friends) are [Matt Pocock's skills](https://github.com/mattpocock/skills),
referenced here rather than republished — used unmodified except `to-prd` and
`to-issues`, which my local copies point at issue files as the canonical record
and extend with a `harden-issues` step and a rubric-shaped criteria template.
`run-issues` builds on the issue conventions his pack establishes.

## Licence

[MIT](LICENSE). Take what's useful.
