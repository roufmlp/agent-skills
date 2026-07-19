# Case study: five issues, one unsupervised day

A real run of [run-issues](../skills/run-issues/SKILL.md), July 2026, on a
multi-tenant procurement SaaS build (Next.js + Supabase, with a Zoho Books
integration). Client and product names are removed; the numbers and defects are
as they happened.

## Where the runner came from

The week before, a bug-hunt round ran as three hand-driven chat sessions of
roughly 730 messages each. Every message re-billed the context behind it, the
sessions stepped on each other through shared files, and a human had to ferry
state between them. That pain produced two skills: `parallel-hunt` for concurrent
rounds, and `run-issues` for sequential issue implementation. The first
`run-issues` outing (a single issue) forced a same-day cost revision: the verify
gate moved to a cheaper model, keeping the strongest model only at the judgment
choke points. This run was the second outing and the first real test: five
issues, dependency-ordered, unsupervised.

## The run in numbers

- Five issues implemented, gated and committed in one day: an accounting
  status read-back, customer document storage, a data-capture field with a
  history of refuting confident beliefs, a deal P&L view, and a read-only
  embedded widget with its own token auth.
- Test suite 857 passing at start, 996 at close. 139 added, zero regressions.
- Three issues passed their gates on the first attempt. One took two. The P&L,
  the issue that computes money, took three attempts and an escalation.
- Every commit passed two adversarial gates: a verify gate that drives the
  running app, and a review gate that reads the full diff and tries to refute it.
- One usage-limit cutoff mid-run; a scheduled wakeup revived the run after the
  reset with no state lost and no context paid twice.

## What the gates caught

**A wrong-record money defect, found by driving.** The first issue's verify gate
rejected on live evidence: entity ids that were workspace-global rather than
deal-scoped meant one deal's screen could surface another deal's record, with a
retry button that would have pushed the wrong document into the client's books.
Every pure test had passed. The fix landed at the seam (two id sets with
different authorities) rather than at the screen.

**A confident wrong margin.** The P&L issue treated "the readings I happen to
have" as "what the books say". With one of two purchase orders unread, the panel
printed an 84.5% margin, captioned "as the books have it", on a deal that makes
14.5%. The gate drove the state, quoted the screen, and rejected. The
implementer patched it; a second driven rejection found the same defect class
surviving in two new places (void documents, ungated gross tiles).

**The two-strike escalation, vindicated.** After two rejections the runner
dismissed the implementer and spawned a fresh one on a stronger model, giving it
both verdicts but none of the failed reasoning. It rejected both prior diagnoses: the root
cause was not void handling or a missing guard, but a data shape that handed
screens independently-nullable figures beside a coverage object and hoped every
consumer would check one before printing the other. It redesigned the type so a
partial total is not a value that exists — reaching a figure requires narrowing
on `known`, and the compiler found every call site. Each new test was proven red
against the old code before the fix was trusted. Enumeration lost twice; making
the bad state unrepresentable won.

**An external API that answers confidently and wrongly.** Live probing found the
integration's status fields flipping to finished values the moment a document is
merely opened, and a documented filter that is silently ignored, returning the
whole org. The defence went in as a shape rather than a comment: the state type
has no field that could carry the lying values, so believing them requires a
type widening plus three failing tests.

**Process failures, owned in writing.** The run's clearest error was its own: two
agents ran concurrently against one rate-limited API org, so the second got
nothing, then polled refusals for an hour. The ledger records it as the
runner's mistake, and it became a rule: shared quotas are run state, one holder
at a time, stop after two refusals. A second catch: a gate declared findings
"routed" to follow-up issues without actually writing them there. Now gates must
cite the append, and the runner greps the target before an issue closes.

## What the post-run review changed

The next day's review fed eight revisions back into the skill:

1. The ledger split from a 40k-token narrative (re-read by every spawn) into a
   thin status table plus a journal only a resuming runner reads.
2. Issues whose acceptance shows a derived money figure now start on the
   strongest model instead of escalating into it two attempts late.
3. Shared external quotas became runner-owned state with a single spend window.
4. Routing of findings is verified mechanically, not taken on declaration.
5. Run worktrees have one writer; commits stage explicit paths only.
6. Verification of server-rendered screens defaults to reading served HTML over
   HTTP, which is cheaper than a browser and immune to a hydration trap that
   once cost a whole session.
7. The preview-deploy step is skipped where it would need a permission the
   sandbox rightly withholds, instead of being re-litigated every run.
8. Review-gate effort floors were examined for savings and deliberately left
   alone. Every cost cut in this list removes waste; none weakens a gate.

## The honest conclusion

A supervised session could have landed five issues. What it could not have done:
earn eleven gate verdicts on driven evidence, catch two money defects that every
pure test missed, and improve its own process from its written record. Quality
was the constraint; cost came down by deleting waste, never by lowering the bar.
