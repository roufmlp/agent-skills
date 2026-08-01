# Global rules — all Claude Code sessions

## Keep this file lean
CLAUDE.md holds pointers and short durable rules only. Never paste long content, docs,
notes, or memory dumps in here. If a body of guidance runs long, give it its own file and
`@import` it. A bloated CLAUDE.md is a bug.

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

## Parallel runs
Any run with two or more concurrent agents on one repo (finder/fixer, bug hunt,
verification round) follows the `parallel-hunt` skill — invoke it before starting,
even if I forget to ask. Never improvise a multi-session run by hand.

## Issue runs
Implementing tracker issues end-to-end (one issue or a range) follows the
`run-issues` skill — same rule: invoke it even if I forget to ask, don't improvise
a long implement session that carries tdd + verify + review in one context.

## The chain, and where to start
A rough idea becomes shipped code through one path, each skill invoked in its own
session: `to-prd` → `to-issues` → `harden-issues` → `run-issues` → merge and
deploy → `parallel-hunt`. A bug report enters as an issue file and goes through
`harden-issues` like anything else. `triage` is out of the chain, decided
2026-07-27. Start at whichever step matches what I actually have; if I hand you
a rough idea and no PRD, that is `to-prd`.

**Nothing in that chain ever stops mid-run to ask me.** Every skill defaults its
open questions, records each default as a default rather than a decision, and
queues it to `.scratch/decisions-queue.md`. Only genuinely irreversible calls wait:
a split, a `wontfix` close, a migration's direction, a money or auth rule, anything
that ships data or commits a public contract. `daily-brief` collects the queues and
carries my answers back out.

## Pending actions on me
Whenever something is pending from me, or you want me to do something: brief me in simple
English, numbered steps, one action each. For any external/manual step (Meta/WhatsApp,
Microsoft 365/Entra/Graph, Zoho, Vercel, Supabase console, registrar, etc.) fetch the
provider's CURRENT official docs first and give today's actual button/menu names — never
remembered/stale UIs — and cite the source. Show a screenshot or a simple visual when it
helps. Split clearly into "you can do now" / "short session with me" / "still on my side
(code)". Save the brief where it will actually be read: anything arising inside the
issue chain goes to the pending-on-abdul file in the repo that work is in, which
`daily-brief` surfaces in section 3 every day. A memory file only for things that
outlive the project.
