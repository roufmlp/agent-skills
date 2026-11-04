Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: grilling
Blocked by: 25

# What the interview settles before a run

## Question

"How a feature with several change notes runs without Abdul" has him answer every stopping question up front on one page, then leave. [The walkthrough](../research/25-walkthrough.md) traced "Report a problem" through that interview and found three gaps, C2, C3 and C4.

No command or skill runs the interview that writes the notes and the approval page. The saved workflow cannot hold a conversation, the page has no path, and nothing tells `/build-feature` that Abdul approved it. The feature's first note writes rights rows and row policies that decide who may read whose reports, and no ticket says whether those count as the page's "sign-in rules" or as the authentication risk class. Last, a done check is a command, and a command naming a spec file that does not exist fails on today's code for that reason alone. It passes the pre-run refusal, and the implementer ends up writing its own done check. Nothing says whether the pre-run check runs while Abdul is still at the keyboard, or who fixes a refused note after he has gone.

Decide what runs the interview and how its approval reaches the run, whether permission rules sit in the authentication class, and who writes the tests behind done checks and when the pre-run check runs.

The lighter option: the interview is `/build-feature`'s first stage, run in Abdul's own session; the approval is a commit of the page; row rules count as authentication; the interview writes each done check's spec as a failing test, and the pre-run check runs before Abdul leaves. A heavier answer says what this would cost.

Changed by "Whether version 2 is built in two stages" (2026-11-01): this ticket belongs to stage two, the careful lane. It is grilled on paper while stage one runs.

## Answer

`/build-feature <name>` becomes a skill with two parts, and the saved workflow it starts is renamed `build-feature-run`, so the two names never collide. With no approved page, the skill runs the interview in Abdul's own session. With an approved page, it checks and starts the run. Abdul learns one command, and typing it again on another day carries on as "How a feature with several change notes runs without Abdul" set out. The skill counts against the plugin budget. The other two options were a lane block of about 15 more lines in every product's `CLAUDE.md`, loaded in every session, and a second command such as `/plan-feature` for the same job.

**Where the interview works.** In its own worktree. It makes the branch `feature/<name>` from local main and commits the notes, their done-check tests and the page there, and the run starts on that branch. Two interviews at the same time never share a checkout, and local main gets nothing until the feature merges. Ticket 19 said the run makes the feature branch; the interview makes it now.

**The page and the approval.** The page is `changes/<feature>/plan.md`, beside the notes and the report. When Abdul writes "approve", the session adds `Approved: <date>` to the page and commits the page and the notes together. The workflow refuses to start when the page has no `Approved:` line, or when a note changed after that commit. A hook that writes the line only when Abdul's own prompt is "approve" would stop an agent approving for him, but it costs one of the four hooks the budget allows, and the approval only ever happens in a session he is in.

**Keeping the interview small.** Subagents read the code each note touches and hand back a short summary each. The interview keeps the summaries, the notes and Abdul's answers. After the approval the session ends and tells Abdul to `/clear`; he types `/build-feature <name>` again in the clean session, which sees the approved page and starts the run with no interview. The session that waits on a run then stays small for days. A session that opens a second session by itself exists only in the desktop app, and the plugin has to behave the same for everyone who installs it.

**Access rules are authentication.** The risk class covers who may sign in and who may read or write which data, so rights rows and row policies count. On the page the question kind "money or sign-in rules" becomes "money or access rules". A wrong permission rule shows one person's data to another, the same harm as a wrong sign-in rule, and version 1 already put this exact choice to Abdul (ruling `q-rp1026-06`, who may send and read problem reports). The five classes stay five.

**Done-check tests.** The interview writes each test file and commits it with its note. It writes Playwright specs against screens that do not exist yet, from the button and label names in the note and the core design. The pre-run check refuses a done check whose test file is missing, since a missing file fails for the wrong reason. The implementer may edit a done-check file when a name changes as the screen is built; the report lists every such edit and the reviewer reads it against the note. Letting the implementer write the tests was lighter, but then it writes the check that grades its own work.

**The pre-run check.** It runs inside the interview, before Abdul sees the page, and a refused note is corrected there. The page he approves is the final one. Its Playwright checks need one build of the app, a few minutes, spent before he approves rather than after he leaves. At every later start, the run checks again the notes that have not started, because main may have moved and the red check ignores done-check tests, which exist before the note. A note whose done check now passes stops as "stopped: done check passes before the work" and goes under "Decide"; the notes that wait for it wait, and the rest carry on.

**Work that is already done.** `/build-feature <name>` refuses when `changes/<feature>/report.md` on local main says "merged", and gives the merge commit. A change to a merged feature is a new feature with a new name, or a one-note change. When a one-note change merges, the session adds `Merged: <date> <commit>` to its note. Before a session builds a one-note change, it runs the note's done checks once on today's code. A `Merged:` line or a passing done check stops the session, which says why. The second test also catches a note that other work already did.

**Two features at once.** Ticket 19 allows two, and with their own folders and their own worktrees their notes, pages and reports never meet. They can still change the same code file or take the same migration number, and that belongs to "What a run does when notes collide or fail".

**Context size across version 2.** Abdul finds that an agent past 300k to 400k tokens makes mistakes, and asked for the limit to hold everywhere in version 2, not only here. That is a wider question than this ticket, so it went to two new tickets: one finds what Claude Code offers to measure and cap a session's context, and one decides the rule.

`CONTEXT.md` now defines interview and feature plan, and the authentication risk class covers access rules.

Changed by "What a run does when notes collide or fail" (2026-11-01): the skill also opens a short interview when the report shows a failed note. Abdul changes or cuts notes there, merged ones included, and approves the changed plan before the run carries on.

Changed by "How every version 2 session stays under 300k tokens" (2026-11-02): the interview writes each of Abdul's answers into `changes/<feature>/plan.md` as he gives it, so a compaction loses none of them.
