# Global rules — all Claude Code sessions

## Keep this file lean
CLAUDE.md holds pointers and short durable rules only. Never paste long content, docs,
notes, or memory dumps in here. If a body of guidance runs long, give it its own file and
`@import` it. A bloated CLAUDE.md is a bug.

## Writing
Everything you write for me follows my writing rules: @writingrules.md

## Design
Any design work (UI, websites, documents, slides) follows my design rules. They are not
loaded by default — invoke the `designrules` skill before starting, every time.

## Code
All code, and especially anything security-relevant, follows my code rules: @coderules.md
Before any app goes live: run the pre-launch gate in that file, every time, no exceptions.

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

## Pending actions on me
Whenever something is pending from me, or you want me to do something: brief me in simple
English, numbered steps, one action each. For any external/manual step (Meta/WhatsApp,
Microsoft 365/Entra/Graph, Zoho, Vercel, Supabase console, registrar, etc.) fetch the
provider's CURRENT official docs first and give today's actual button/menu names — never
remembered/stale UIs — and cite the source. Show a screenshot or a simple visual when it
helps. Split clearly into "you can do now" / "short session with me" / "still on my side
(code)". Save the brief where it's read every session (a memory file).
