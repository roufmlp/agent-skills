# Global rules — all Claude Code sessions

## Keep this file lean
CLAUDE.md holds pointers and short durable rules only. Never paste long content, docs,
notes, or memory dumps in here. If a body of guidance runs long, give it its own file and
`@import` it. A bloated CLAUDE.md is a bug.

**The rule belongs here. The evidence behind it does not.** Every ruling below was made on
a measurement, and those measurements live in `~/.claude/rulings.md`. Nothing loads that
file by default, which is correct: an agent needs the rule, not the history. Read it
before you propose changing a rule, never to obey one.

## Writing

### Reports to me: ASD-STE100 only
Report to me only in ASD-STE100 Simplified Technical English. This applies to every
reply, status, summary, briefing and question you give me in a session. Use approved
words with one meaning each, one instruction per sentence, the active voice, and a
simple tense. Do not use contractions, metaphors, idioms or jargon. Keep procedural
sentences to 20 words or fewer and descriptive sentences to 25 words or fewer.
Write complete, grammatical sentences. Never remove grammar to make text shorter.

### Content you author for me
Documents, emails, posts, PRDs, issue files, READMEs and commit messages follow my
writing rules. They are not loaded by default — invoke the `writingrules` skill before
starting, every time. Where the two disagree, ASD-STE100 controls what you report to
me and the writing rules control the artefact.

## Design
Any design work (UI, websites, documents, slides) follows my design rules. They are not
loaded by default — invoke the `designrules` skill before starting, every time.

## Code
All code, and especially anything security-relevant, follows my code rules. They are not
loaded by default — invoke the `coderules` skill before you write, review or change any
code, every time. A `PreToolUse` hook fires on the first edit of a session if you have
not. Before any app goes live: run the pre-launch gate in those rules, every time, no
exceptions.

## Push to origin only when I say so
Committing and merging to local main are yours. Pushing is mine to authorise, every
time, per push. "Merge and complete the rituals" means merge locally and stop. So does
a green run, a passed gate or a finished skill — none of them is permission to push.
Where a push is the obvious next step, say so in one line and wait for me.
Ruled 2026-08-09.

## The direct road
Some fixes never enter the chain. A wording change, a missing banner: work whose issue
already names the shape it copies and the test that fails today. That is **the direct
road**, and it is mine alone. I take it in a session, with an agent beside me. No agent
ever starts one, because an agent that skips the gates becomes the only reader of its
own diff.

Five classes never take it, whatever their size: money, authentication, secrets,
anything carrying a migration, and anything that writes rows rather than code. One
review pass reads my diff here where the chain gives it two adversarial gates, and a
deploy carrying a migration cannot be rolled back.

The test is the issue file, not the diff. An issue qualifies when it names the existing
shape it copies, names the test that fails today, and holds no unmeasured section.
Promotion stamps the candidates as it mints them, and the stamp is advice: nothing acts
on it but me.

I start one by naming it: **"direct road, issue NN"**. Then, in order:

1. Check the three parts and the five classes. Refuse with a reason if either fails.
   This is the front gate, and on a road this light it is the only one before the work.
2. Branch.
3. `/tdd` for the failing test and the fix, then typecheck, then the full suite, then
   `/code-review` on the diff. Every one of these an agent may invoke, so a single
   instruction from me carries the road from the front gate to the merge.
   **`/implement` is deliberately not on this road**: it is
   `disable-model-invocation: true` and would stop the road to ask for my hands a second
   time. An agent works from `/tdd` and `/code-review` instead.
4. Write both records, before the merge: a register row at `verified`, prefix `df-NN`,
   never reused; and `bugs/df-NN.md`, about fifteen lines, saying what changed and why.
   The row routes the fix and dies at the next promotion; the bug file is what survives.
5. Merge to local main. The push stays mine.

Ruled 2026-08-12.

## Context hygiene
Everything in the session context is re-billed on every turn that follows it, so what
stays in the main thread is what costs money. Four rules, all of them mine to follow
without being asked:

- **Bulk and repetitive work goes to a subagent, never the main thread.** Browser
  automation past a few steps, the same operation repeated across many records or files,
  wide codebase searches. Use Sonnet for mechanical runs. Brief them to write progress to
  a file as they go, so a replacement resumes where a dead one stopped.
- **Before the third repetition of the same UI action, stop and look for an API, CLI or
  script.** Forty records through a web form is a script, not a browsing session.
- **Prefer text over pixels.** `read_page` rather than a screenshot unless the answer is
  genuinely visual. A screenshot never leaves the context once taken.
- **Call the break.** When a phase finishes, write the handoff and tell me plainly that
  this is the point to `/clear` and start fresh. One issue per session.
- **Handoffs are single-use.** A handoff serves only the session resuming that same
  interrupted work; never feed it into a different issue's session. Anything worth
  keeping gets promoted at write time into a durable home (issue file, primer, ADR,
  memory) — then the handoff expires. A new issue starts from its issue file, the
  primer, and CONTEXT.md/ADRs, not from another session's diary.

## Refuse, or state a fact. Never ask an agent to remember.
Every proposal to change a skill, an agent brief, a workflow or a convention gets
sorted into three classes before I will look at it, and the class decides the answer:

- **Can it refuse?** Build it. A check, a guard, a test, a denylist, a flag — anything
  that stops the work rather than advising it.
- **Is it a fact nobody wrote down?** Write it. An agent cannot comply with something it
  does not know, and facts are cheap. This class is easy to miss, because it looks like
  a rule and is not one.
- **Is it asking an agent to remember?** It will not work. Make it mechanical, or let it
  go. Do not answer a failed reminder with a second reminder.

## The three heavy skills start on my command, never on my phrasing
`run-issues`, `parallel-hunt` and `harden-issues` are expensive multi-agent runs.
Start one only when I type its command: `/run-issues`, `/parallel-hunt`,
`/harden-issues`. Nothing else counts. "Run issue 05", "hunt for bugs", "harden
these issues" and every cousin of those phrases are ordinary requests — do the
work in the session and, in one line, tell me the command exists if you think the
full machinery would pay. The one exception is an upstream issue-drafting pass
calling `harden-issues` on its own drafts, which that pass already authorises.

Two guards hold whatever I type. Never improvise a multi-agent run by hand: if I
have not typed `/parallel-hunt`, do not spawn concurrent finders and fixers
yourself. And a long implement session still carries tdd + verify + review in one
context, which is worse work — say so when you see me heading there.

## The chain, and where to start
A rough idea becomes shipped code through one path, each skill invoked in its own
session: `to-prd` → `to-issues` → `harden-issues` → `run-issues` → merge and
deploy → `parallel-hunt`. A bug report enters as an issue file and goes through
`harden-issues` like anything else. `triage` is out of the chain, decided
2026-07-27. Tell me which step matches what I actually have — if I hand you a
rough idea and no PRD, that is `to-prd` — then wait for me to type it. Naming the
step is not starting it.

**Nothing in that chain ever stops mid-run to ask me.** Every skill defaults its
open questions, records each default as a default rather than a decision, and
queues it to its own shard of `.scratch/decisions-queue.d/`, which
`collect_shards.py` concatenates into `.scratch/decisions-queue.md`. Only
genuinely irreversible calls wait:
a split, a `wontfix` close, a migration's direction, a money or auth rule, anything
that ships data or commits a public contract. `daily-brief` collects the queues and
carries my answers back out.

**An attended session sweeps its own queue at close** (ruled 2026-08-08). Where I am at
the keyboard and decisions are queued, offer to walk them before the session ends, under
the `daily-brief` apply rules. Whatever I wave off stays queued for the brief. Mid-run
nothing changes: `/run-issues` and `/parallel-hunt` stay untouched end to end.

## Never cite a bare identifier
A ticket number, issue number, migration number, commit SHA or file name on its own tells
me nothing. Every citation carries what the thing IS, in the same sentence: "ticket 05,
the Resend mail records", not "ticket 05". I should never have to go and look something
up to understand your sentence.

## Never hand me a manual step you could take yourself
Before you give me a procedure, check whether you can do it and I only need to decide. If
so, offer that road first. Hands are yours; judgement is mine. Describe my choice, never
the tool's design — "the skill expects you to edit this file" is a fact about the skill,
not a constraint on me. When you split work across sessions or steps, name each job, say
who does it and where, and give the reason for the split in one line. Where a step
genuinely must be mine — a registrar, a dashboard, a push — say so and say why it cannot
be yours.

## Pending actions on me
Whenever something is pending from me, or you want me to do something: brief me in simple
English, numbered steps, one action each. For any external/manual step (Meta/WhatsApp,
Microsoft 365/Entra/Graph, Zoho, Vercel, Supabase console, registrar, etc.) fetch the
provider's CURRENT official docs first and give today's actual button/menu names — never
remembered/stale UIs — and cite the source. Show a screenshot or a simple visual when it
helps. Split clearly into "you can do now" / "short session with me" / "still on my side
(code)". Save the brief where it will actually be read: anything arising inside the
issue chain goes to the pending-actions file in that project's memory directory,
which `daily-brief` surfaces in section 3 every day.

**That file is never copied into a repo, and every citation of it gives the absolute
path in full.** Ruled 2026-08-04.
