Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: task (AFK)
Blocked by: 22, 23, 24

# Walk two real cases through version 2

## Question

Twenty-four tickets decide version 2 one part at a time, and the gaps sit between the parts. Three surfaced on 1 November from plain questions about real use: whether the implementer works test-first, whether the tests work on .NET, and whether anyone clicks the new buttons. An agent that builds from the spec fills every gap like these with its own default, and Abdul meets the default only when he uses the product.

Trace two cases through version 2 on paper, one step at a time, from the first message to the last:

1. A new MVP in the fast lane, from an idea picked at the brainstorm session to done. Use an idea from the private `roufmlp/ideas` repo if it holds one; otherwise make up a small one and say so.
2. A careful-lane feature of three or more change notes on Orderflow, from the interview to the merge on local main and the push. Take a real feature from Orderflow's git log, so the trace meets real screens, migrations and tests.

At each step, name who acts (Abdul, which agent, which script or hook), what they read and write, and the ticket that decides it. A step that no ticket decides, or that two tickets decide differently, is a gap. For each gap, write the step, what is missing and the tickets that come closest.

This is agent work with nothing to decide. Abdul reads only the list of gaps. Each gap that needs his call becomes a grilling ticket on this map; a gap that one ticket's answer already settles by plain reading is noted and closed in the file. The trace goes to `research/25-walkthrough.md`, and the spec carries both traces so Abdul can see what version 2 does before anyone builds it.

The gap list also carries one question the map has not asked yet: whether the build goes in two stages, the fast lane first and used on one real MVP before `/build-feature` and the careful lane are built. Put the case for and against at the top of the gap list.

## Answer

Both cases are traced in [the walkthrough](../research/25-walkthrough.md). Case 1 is a client's kit site, a real fast-lane MVP whose brief was grilled on 27 October; the ideas repo does not exist yet, so its pick at the 1 December brainstorm session is made up. The client's name is private, so the trace calls it the kit site. Case 2 is Orderflow's "Report a problem", version 1 issues 666 to 675, which becomes ten change notes with five migrations.

The traces found 23 open gaps, 12 in the fast lane and its seams and 13 in the careful lane, plus 5 that one ticket settles by plain reading. The 5 are closed in the research file. The 23 went to eight grilling tickets rather than one each, grouped so that a session can settle each group in one sitting:

- [Whether version 2 is built in two stages](26-two-stage-build.md), the question the brief asked for, with the case for and against at the top of the gap list.
- [How the ideas repo and the brainstorm routine run](27-ideas-repo-and-routine.md)
- [How an MVP's limits and its end are recorded](28-mvp-limits-and-record.md)
- [How a change goes live](29-going-live.md)
- [How a product graduates, stops or switches over](30-graduate-stop-switch.md)
- [What the interview settles before a run](31-interview-before-a-run.md)
- [What a run does when notes collide or fail](32-collisions-and-failures-in-a-run.md)
- [Where the note check lives, and baselines for changed screens](33-note-check-and-changed-baselines.md)

Two of the gaps carry real risk. Nobody owns applying a migration to production before the push that deploys its code, and nobody owns the pre-launch gate inside a run. Both sit in "How a change goes live".

The spec carries both traces, updated by the answers to these eight tickets, so Abdul can see what version 2 does before anyone builds it.
