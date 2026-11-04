# Walking two real cases through version 2

Two cases, traced one step at a time against the 24 resolved tickets. Case 1 is a new MVP in the fast lane: a client's kit site, whose real brief was grilled on 27 October. Case 2 is a careful-lane feature on Orderflow: "Report a problem", version 1 issues 666 to 675, which becomes ten change notes. Case 1 has 19 steps and case 2 has 34.

They found 23 open gaps and 5 that one ticket already settles by plain reading. Gaps from case 1 are numbered F1 to F12 and gaps from case 2 C1 to C13. The open gaps go to eight new grilling tickets, listed below; Abdul reads only this first part. The two traces follow it, each with its gaps in full.

## Build in two stages?

The map plans one build and one switch. The other road builds the fast lane first, uses it on one real MVP, then builds `/build-feature` and the careful lane.

For two stages: the fast lane is a small part of version 2 (the ideas repo, the routine and its prompt, the brief and `CLAUDE.md` templates, the code and design rules skills, the live-key deny and the side-by-side page). Eight of its ten open gaps sit in steps one real MVP would meet. The kit site already runs a fast lane under version 1 and has broken two of its limits, which is cheap evidence. The careful lane's thirteen gaps can be grilled on paper while stage one runs.

Against: Orderflow and procurement stay on version 1 until the careful lane exists ("What happens to Orderflow": "Version 2 must be built"), with its 33 hooks and an evening check that starts fixes on its own, on the one product that holds real orders. An MVP that graduates in stage one has nowhere to go, because graduation needs the core design, the checks and the baselines. Two sets of global rules would be in force at once.

My lean is two stages, with graduation held until stage two lands. Orderflow already stays on version 1 until request-kinds finishes, so some overlap happens either way, and the careful lane's gaps are the ones that can cost a real business money or data. They deserve the extra weeks. [Whether version 2 is built in two stages](../issues/26-two-stage-build.md) decides it.

## Open gaps, by the ticket that takes them

[How the ideas repo and the brainstorm routine run](../issues/27-ideas-repo-and-routine.md)
- F1. No ticket creates `roufmlp/ideas` or gives its files a layout, yet the audit's Speed row needs dates from it.
- F2. The cloud brainstorm session has no brief template, grilling skill, writing rules or ASD-STE100 rule, and the routine's prompt has no home.
- F3. Nothing says where the page lives, how a run knows the last session went unopened (which decides whether a keep is spent), or what gives way when the page on the 1st runs past one page.
- F4. Four writers push to the ideas repo, against "push only when Abdul says so", and routine output lands on `claude/` branches the next run cannot see.

[How an MVP's limits and its end are recorded](../issues/28-mvp-limits-and-record.md)
- F5. No ticket says when an MVP joins the list, whether one still in its prototype must take a result and spend its keep, or who writes "done".
- F6. Nothing checks the one-page, one-day and three-day limits. The kit site broke two of them.
- F10. The side-by-side page has no tool, and "difference" means nothing when fake data meets test data.

[How a change goes live](../issues/29-going-live.md)
- F8. No ticket says who creates an MVP's hosting, whether a deploy counts as a push, or whether an unattended build session may deploy.
- C12. The pre-launch gate before the push has no owner among the run's roles and no place relative to the merge to local main.
- C13. No ticket says who applies migrations to production, when, or that they go in before the push that deploys the code.

[How a product graduates, stops or switches over](../issues/30-graduate-stop-switch.md)
- F11. Graduation and stopping draw on seven tickets with no procedure, no home and nothing that starts them.
- F12. A product named after its client meets the `commit-msg` hook in the README.
- C1. Orderflow's core design sources hold no screen list with routes and no module map, and no switch step writes them or a screenshot test.

[What the interview settles before a run](../issues/31-interview-before-a-run.md)
- C2. No command or skill runs the interview, the approval page has no path, and nothing tells `/build-feature` it was approved.
- C3. No ticket says whether rights rows and row policies count as sign-in rules and the authentication risk class.
- C4. No ticket says who writes the test behind a done check, or when the pre-run check runs relative to Abdul leaving.

[What a run does when notes collide or fail](../issues/32-collisions-and-failures-in-a-run.md)
- C5. The red check does not say whether a new migration is source, or how the test database is rebuilt.
- C8. Two parallel notes both take migration 0077 and git merges both cleanly.
- C9. After a note fails three times, nothing says whether it retries, who rewrites it or whether the final check runs on the rest.
- C10. The final check tests the feature branch, then the merger merges into a main that moved.
- C11. The final fix round skips the red check and the hostile walk.

[Where the note check lives, and baselines for changed screens](../issues/33-note-check-and-changed-baselines.md)
- C6. The note check is not among the plugin's four hooks, and its kind, install and commit-to-note map are unstated.
- C7. Nobody is named to retake baselines for screens a note changes on purpose, or to approve them.

## Settled by plain reading

- F7. Who writes an MVP's `CLAUDE.md`. The prototype session, which creates the MVP's repo ("How the brainstorm session works": the brief moves there "until the prototype session creates the MVP's own repo").
- F9. The global line "before any app goes live" does not gate an MVP deploy. "What the fast lane does": "the gate's own trigger is 'real users or real data'". The new global `CLAUDE.md` should use that wording.
- C, step 11. The verifier runs before the reviewer, so an attempt earns one strike at most ("What the careful lane keeps", lane steps 3 to 5).
- C, step 29. Abdul's push is his approval of new baselines ("What the verifier checks in the browser": "which is already his step").
- C, step 4. A new pattern that adds no screen needs no prototype ("What the verifier checks in the browser" and "How the careful lane keeps every slice aligned").

## Case 1: a new MVP in the fast lane

### The idea

`roufmlp/ideas` does not exist, so there is no idea log to draw from. I used a real idea instead: a client's kit site, whose fast-lane brief sits in the MVP's own private repo. It was grilled with Abdul on 27 October 2026 under version 1. The client is a merchandise firm with no website. The MVP is an eight-page Astro site on Vercel whose main flow takes a sports club manager from `/sports` into a kit designer and out through a two-step enquiry, sent as an email with the design attached as a PNG. The private repo holds 11 commits, a prototype under review, and 12 done checks.

In real life the idea came straight from a client and skipped any brainstorm. To trace the case as asked, I pretend Abdul put it in the idea log as one line in late November and picked it at the 1 December session. The brief's content, its stack and its done checks are real; the dates from 1 December on are made up.

The client's name is private under "What in this repo is private" and "One repo that is safe to publish" (tickets 06 and 09), so this trace calls the product the kit site.

### Setup, once

**S1. Create the ideas repo.**
Who: no ticket names anyone. Reads: nothing. Writes: a private GitHub repo `roufmlp/ideas` holding the idea log and the MVP list.
Decided by: 07 (brainstorm session) says the repo holds the log and the list; 08, 14 and 18 add open change-note lines, weekly audit summaries and parked products. None says who creates it or what each file looks like. **GAP F1.**

**S2. Set up the brainstorm routine.**
Who: Abdul, through `/schedule` or claude.ai/code/routines. Reads: nothing yet. Writes: a cloud routine with cron `0 9 1,15 * *`, cloning `roufmlp/ideas` and able to read the latest check result on `roufmlp/agent-skills`.
Decided by: 05 (scheduling options) and 07. The first run must confirm two things 05 left open: that the cron field takes `1,15`, and whether a finished run notifies Abdul. If it does not, a calendar event on the same dates stands in (07). The routine's prompt, which carries everything the session must do, has no named home. **GAP F2.**

**S3. Set up the weekly audit script.**
Who: a build session writes it; a desktop scheduled task runs it every Sunday on the laptop. Reads: new session transcripts. Writes: a summary of a few KB, pushed to `roufmlp/ideas`.
Decided by: 14 (workflow audit). The script pushes with nobody there. **GAP F4.**

**S4. The laptop is ready.**
Who: the switch session, already done. Reads and writes: the working copy at `~/.claude/skills/workflow/`, Matt Pocock's plugin installed once, the live-key hard deny in the private settings, and the brief and `CLAUDE.md` templates inside the plugin.
Decided by: 09 (one public repo), 10 (install path), 11 (version story), 16 (steering files). No gap for this case.

### The case

**1. The idea enters the log.**
Who: Abdul, or a session he asks. Reads: the idea log. Writes: one line, "Website for the kit client: sports clubs cannot see the kit or ask for a quote".
Decided by: 07. The write has to reach the repo's GitHub copy, or the routine never sees it. **GAP F4.**

**2. Sunday 29 November: the weekly summary.**
Who: the audit script (S3). Reads: the week's transcripts. Writes: a summary pushed to `roufmlp/ideas`.
Decided by: 14.

**3. Tuesday 1 December, 09:00 UTC: the routine prepares the page.**
Who: the cloud routine, from a fresh clone. Reads: the idea log, the MVP list, the change-note lines, the parked products, the audit summaries and the install check result. Writes: up to three researched ideas, each with a source, into the log, then the page. The page has the open MVPs (none yet), a shortlist of at most five ideas ranked with a first choice and one reason, each parked product by name, the line "Install check: passing", and, because it is the 1st, the audit table and one line per proposal.
Decided by: 07, 08, 10, 14 and 18. The tickets do not say where the page lives, how a run tells that last time's session was never opened, or which part gives way when the page on the 1st runs past one page. **GAP F3.** The log additions are writes to the ideas repo. **GAP F4.**

**4. Abdul learns the page is ready.**
Who: the routine's notice, or the calendar event. Reads and writes: nothing.
Decided by: 05 and 07, once the first run settles which.

**5. Abdul runs the session: review, then pick.**
Who: Abdul, in the routine's own session on claude.ai. Reads: the page. Writes: no MVP results (none is open); yes or no on each audit proposal; the kit site marked as picked in the log, with a reason for each idea he turns down.
Decided by: 03 (graduation test), 07 and 14.

**6. The draft brief.**
Who: Claude interviews Abdul in the same cloud session. Reads: the idea, the shortlist entry, Abdul's answers. Writes: a draft brief in the ideas repo, with the six parts from 01 and the prototype link empty.
Decided by: 01 (fast lane) and 07. The cloud session has none of `~/.claude/` and no working copy of the plugin, so it has no brief template, no grilling skill, no writing rules and no ASD-STE100 rule for its reports. **GAP F2.** The brief carries no stack line and the session sets no rule on stack choice, as 23 (other stacks) ruled; Astro is allowed. Whether the kit site now goes on the MVP list, and from what date its age counts, no ticket says. **GAP F5.**

**7. The prototype session.**
Who: Abdul and a local Claude Code session. Reads: the draft brief, the design rules (the `designrules` skill). Writes: a private GitHub repo for the MVP; the brief moved in from the ideas repo and linked from the log; `CLAUDE.md` from the template with "Lane: fast"; the prototype in Astro with fake data; a screenshot of each screen; the prototype link that finishes the brief. Abdul approves the prototype, and its code becomes the first commit. He pushes it.
Decided by: 01, 07, 16 and 23. Ticket 16 says "the brief session" writes `CLAUDE.md`, and an MVP has no session by that name. **GAP F7** (settled). The one-day limit and the one-page brief have nothing that checks them. The real case broke both: the prototype has been under review from 27 October to 1 November across five worktrees, and the brief runs to about two and a half pages. **GAP F6.**

**8. The build session.**
Who: one Claude Code session in auto mode, started by Abdul, with `/goal` set to the 12 done checks. Reads: the brief, `CLAUDE.md`, the prototype code and, after a context reset, the git log. Writes: one small feature at a time on top of the prototype, with tests and typecheck after each; commits merged to local main.
Decided by: 01 and 08 (careful lane keeps). The `coderules` skill must load before the first edit, or `coderules-gate` refuses it (10, 16). Test-first is the session's choice (22). The hooks that ship (10) and the live-key hard deny apply. If the context fills, Abdul starts a fresh session that carries on from the brief and the git log. The three-day limit has nothing that checks it. **GAP F6.**

**9. The MVP goes live.**
Who: no ticket says. Reads: the brief's "test-only" part. Writes: a Vercel project, its environment variables (the test inbox, the Resend key, `SITE_ENV=mvp`) and a deploy to a `*.vercel.app` address.
Decided by: 01 says done means "live at a public URL" and that Abdul approves each push. It does not say who creates the Vercel project, whether a deploy counts as a push, or whether the build session may deploy without him. Done check 3, a real send through the deployed function, cannot pass until this step happens, so `/goal` stalls if the agent may not deploy. **GAP F8.** The global `CLAUDE.md` says the pre-launch gate runs "before any app goes live", which reads as a gate on this deploy. **GAP F9** (settled). Resend has no test mode, but its onboarding sender delivers only to the account owner, which 01's "Stripe test mode and test accounts are fine" covers.

**10. Browser pass and review.**
Who: the build session, then `/code-review` in a fresh context. Reads: the main flow in the running app; the diff against the brief. Writes: fixes for what the review finds.
Decided by: 01. The fast lane gets no hostile walk (24). Ticket 10 already lists the open check that a bare `/code-review` still reaches the built-in review now that Matt Pocock's plugin has a skill of that name.

**11. The side-by-side page.**
Who: the build session makes it; Abdul approves it. Reads: the prototype screenshots and new screenshots of the MVP. Writes: one page with every difference marked and each screen the prototype lacked marked "new".
Decided by: 01 and 24 (browser verification). No ticket names the tool that builds the page or says what counts as a difference. **GAP F10.**

**12. Abdul uses it once.**
Who: Abdul. Reads: the live site. Writes: one enquiry with a kit design, which lands in his own inbox.
Decided by: 01.

**13. Done is recorded.**
Who: no ticket says which session. Reads: Abdul's word that he used it and approved the side-by-side page. Writes: the MVP's line in the list marked done with a date, the idea log updated, and any action only Abdul can take under "Do" in `~/.claude/pending.md`.
Decided by: 07 ("whichever session changes an MVP updates its line") and 16 (pending file). The build session may end before Abdul uses the site, so nobody is placed to write "done". **GAP F5.** The write goes to the ideas repo. **GAP F4.**

**14. Tuesday 15 December: the next page.**
Who: the cloud routine. Reads: the MVP list. Writes: the kit site under open MVPs with its age and a suggested result.
Decided by: 03 and 07. The age depends on GAP F5.

**15. Abdul gives the MVP its result.** Three branches.

**15a. Graduate.**
Who: Abdul decides in the brainstorm session; a local graduation session does the work. Reads: the brief, the MVP code, the approved prototype, the code rules. Writes: one line in the brief with the date, the person (the client's operations team, who will get real enquiries within a week) and the reason. Then the pre-launch gate, all ten steps, several of which do not apply to a static site with no database or sign-in. Then `docs/design.md` with its screens, patterns and modules, a check for each pattern, the import rules, a baseline screenshot of every screen at 390 and 1280 pixels, a port-list column for Astro and `node --test`, and `CLAUDE.md` rewritten to "Lane: careful" with a 5-minute suite budget and the test command. Only then does the first real thing go in: the three environment variables, the move to the client's domain and Search Console.
Decided by: 03, 08, 15 (alignment), 16, 21 (suite speed), 23 and 24. No skill, template or command holds this list, and the cloud session where Abdul decides cannot run it. **GAP F11.** If the product is listed in the README's products section, it carries the client's name, which the `commit-msg` hook refuses. **GAP F12.**

**15b. Keep.**
Who: Abdul. Writes: keep count 1 on the MVP's line. At the 1 January session it must graduate or stop.
Decided by: 03 and 07. A session Abdul never opens does not use up the keep (07), which depends on GAP F3.

**15c. Stop.**
Who: no ticket says. Writes: the Vercel deploy taken down, the Resend test key revoked, the repo archived on GitHub, the MVP's line marked stopped.
Decided by: 03 and the glossary entry for "stopped". Ticket 18 found that pausing a Vercel project needs Abdul to type its name, so part of this step is his, and the cloud session cannot do any of it. **GAP F11.**

### Where the fast lane touches the careful lane

- The pre-launch gate. The global `CLAUDE.md` gates "any app" going live, while the fast lane deploys an MVP with no gate. Ticket 01 settles it (GAP F9), but the rewritten global file has to carry the narrower wording.
- Graduation. Every careful-lane artefact is born here: the core design, the pattern and module checks, the baselines, the lane block, the suite budget and the port. No procedure holds them together (GAP F11).
- The port list. The kit site runs Astro with `node --test`, so the scoped run and the red check, both named for vitest, have no value for it until the graduation session fills a column. Ticket 23 says this is the plan, so it is not a gap; it does mean the first careful-lane change on the kit site waits for a port nobody has costed.
- Inherited tests. Test-first is optional in the fast lane (22), and the red check runs only on tests a change note adds. An MVP's own tests enter the careful lane with no check that they can fail. No agent has to invent anything here, so it is not a gap, but it is a hole Abdul may want to know about.
- Screenshots. The prototype was shot at 1440 and 390 pixels; careful-lane baselines are 390 and 1280. The baselines are taken fresh at graduation (15), so nothing breaks.

### Gap detail, case 1

**GAP F1. Nobody creates the ideas repo, and its files have no layout.** Step S1, used again in steps 3, 6, 13 and 14. Ticket 07 says what the repo holds, and 08, 14 and 18 add to it, but no ticket creates it or says what a line holds. The audit's Speed row (14) needs an idea date and a live date from it, and the page (18) needs a list of parked products. Closest: 07, 14, 18. Judgement: needs a decision, but a small one. A build default (one Markdown file per list, fixed fields per line) would do, and Abdul only needs to hear which session creates the repo, the switch session or the first routine.

**GAP F2. The cloud session has none of Abdul's skills or rules, and the routine's prompt has no home.** Steps S2 and 6. The brainstorm session writes a draft brief by interview, yet it starts from a fresh clone of `roufmlp/ideas` with no working copy, no `~/.claude/`, no brief template, no grilling skill, no writing rules and no ASD-STE100 rule. Making the ideas repo turn on the published plugin would bring the templates but not the private writing rules, and a copy of those breaks 16's "no other copy". Closest: 05, 07, 10, 16. Judgement: needs Abdul's call.

**GAP F3. Where the page lives, how the routine knows it went unopened, and what gives way on the 1st.** Step 3, also 15b. Ticket 07 says a run that finds last time's session unopened "updates that page rather than making a second one", but a routine starts from a fresh clone and cannot see whether a claude.ai session was opened. The unopened rule also decides whether a keep is used up. Separately, on the 1st the page holds the MVPs, five ideas, parked products, change-note lines, the install line and a half-page audit table, which can pass the one-page limit the map sets. Closest: 05, 07, 14. Judgement: needs Abdul's call on the first part (for example a status file in the ideas repo that the session writes when he opens it); the second can be a build default if he accepts that the audit table may push the page past one page on the 1st.

**GAP F4. Writes to the ideas repo against "push only when Abdul says so".** Steps S3, 1, 3, 6 and 13. The global push rule, which 16 keeps, makes every push Abdul's call. Yet the weekly script pushes summaries with nobody there, the routine adds ideas, the brainstorm session writes the log and the draft brief, and build sessions update the MVP list. Research 05 adds that a routine's output lands on `claude/` branches and PRs by default, so the next run's fresh clone of the default branch would not see the last run's writes. Closest: 07, 14, 16, 05. Judgement: needs Abdul's call: whether pushes to the private ideas repo are exempt from the push rule, and whether routines may push to its default branch.

**GAP F5. When an MVP joins the list, when it counts as done, and whether an unfinished one gets a result.** Steps 6, 13 and 14. Ticket 03 says the session gives "every MVP that is not yet a product" a result, and 07 tracks "age and keep count". Neither says whether the line starts at the pick, the prototype or the deploy, nor whether an MVP still in prototype at the next session must take graduate, keep or stop and use its keep. Nor does any ticket place the "done" write, which needs Abdul's word that he used the site, often after the build session has ended. The kit site would have reached the 15 December session still in its prototype on the real timeline. Closest: 03, 07, 14. Judgement: needs Abdul's call on the unfinished-MVP rule; the rest follows from it.

**GAP F6. The fast lane's limits have nothing that checks them.** Steps 7 and 8. Ticket 01 sets one page for the brief, one day for the prototype and three days for the MVP, and says "at each limit Abdul cuts scope, carries on or stops". No script measures a limit, nothing raises the question, and nothing records his answer. The real case broke two of the three: about two and a half pages and 12 done checks, and a prototype under review for five days. By Abdul's own rule that a reminder is not a control, these limits are reminders. Closest: 01, 14 (the Speed row measures afterwards). Judgement: needs Abdul's call: build a check (a word count on the brief, dates on the MVP list that the session-start hook compares), or accept the limits as advice.

**GAP F7. Who writes an MVP's `CLAUDE.md`.** Step 7. Ticket 16 says "The brief session writes the file from a template of about 15 lines", and an MVP has no session by that name. Judgement: settled by plain reading. Ticket 07 has the draft brief sit in the ideas repo "until the prototype session creates the MVP's own repo, then moves there", and "the brief is finished when Abdul approves the prototype". So the prototype session finishes the brief and owns the new repo, and it writes `CLAUDE.md`. Close it with that line in the spec.

**GAP F8. How an MVP goes live.** Step 9. Done needs "live at a public URL" (01), and 01 keeps "Abdul approves each push". No ticket says who creates the hosting project and sets its test variables, whether a CLI deploy counts as a push, or whether an unattended build session may deploy. A done check that needs the live site, such as the kit site's real send, makes `/goal` wait on the answer. Closest: 01, 16. Judgement: needs Abdul's call.

**GAP F9. The global gate line against an ungated MVP deploy.** Step 9. Today's global `CLAUDE.md` says "Before any app goes live: run the pre-launch gate", and 16 keeps the code pointer that carries it. The MVP goes live with no gate. Judgement: settled by plain reading of 01: "The step from test to real is graduation, and that is where the pre-launch gate runs, since the gate's own trigger is 'real users or real data'." The new global file should use the code rules' own trigger.

**GAP F10. The side-by-side page has no tool, and "difference" has no meaning.** Step 11. Ticket 01 asks for each difference marked, and 24 gives the careful lane's feature report the same layout, but neither names what builds the page. Prototype screenshots hold fake data and the MVP's hold test data, so a pixel diff marks every screen, and Orderflow's fidelity tool produced 2,175 difference rows that never blocked anything (15). Closest: 01, 15, 24. Judgement: needs Abdul's call, a short one: does the agent mark the differences it judges intended and unintended, or does a script mark every one?

**GAP F11. Graduation and stopping have no procedure and no home.** Steps 15a and 15c. Graduation draws on seven tickets (the gate, the core design, checks, baselines, the lane rewrite, the suite budget and the port), and none says what starts the session or where its list lives. The plugin carries four skills of Abdul's, none for this. Stopping has the same problem, and part of it is Abdul's because pausing a Vercel project asks him to type its name (18). The brainstorm session where he decides runs in the cloud and can do neither. Closest: 03, 15, 16, 18, 21, 23. Judgement: needs Abdul's call: a graduation skill or a template in the plugin (which counts against the budget in 14), or a checklist in the spec that the session reads.

**GAP F12. A product named after its client.** Step 15a. Ticket 09 makes product names public and client names private, and the glossary says "a product's own name is not a private name". Here the product carries the client's name. Once the client is on the private-name list, the `commit-msg` hook refuses the README's products entry (11), and this trace too, if it goes public with the map. Closest: 09, 11. Judgement: needs Abdul's call, at graduation at the latest: list such a product under a neutral name, or keep client work out of the products section.

## Case 2: a careful-lane feature on Orderflow

### The feature

**Report a problem.** Any signed-in person taps a speech bubble in the phone header (or "Report a problem" at the foot of the laptop sidebar), types a sentence and sends it with a screenshot of the page behind the sheet. Each person sees their own reports on a new "My reports" page, and gets an alert and a phone push when one turns Fixed or Closed. The evening check reads every report through a database principal of its own.

In version 1 it ran as issues 666 to 679 in run `batch-0b441f`: 14 issues, 12.95 hours, five migrations, and one issue (668, the screenshot) that took three strikes and a carve.

- Commit range: `95f1e5a12` (26 October, "Record the report-a-problem request, its approved mock-up and three rulings") to `edbd6d802` (27 October, "Close run batch-0b441f at its merge and mint its two carved parts"). The code commits run from `bd2a4d099` (issue 666) to `6b13a42dc` (issue 679).
- Migrations: `0076_problem_reports.sql`, `0077_problem_report_screenshot.sql`, `0078_report_hint.sql`, `0079_evening_check.sql`, `0080_report_alert.sql`.
- Screens: every signed-in screen, through `src/app/(signed-in)/layout.tsx` and `src/controls/layout/shell-frame.tsx`; the new `src/app/(signed-in)/my-reports/page.tsx`; the error page `src/app/(signed-in)/error.tsx`; the alerts list.
- Tests: `tests/problem-reports/` (send, read, rights, screenshot-send, report-hint, outbox, my-reports-page, outcomes, report-alert and others), `tests/rights/matrix.test.ts`, `tests/evening-check/route.test.ts`, and the end-to-end specs `e2e/report-a-problem.spec.ts`, `e2e/report-hint.spec.ts`, `e2e/report-a-problem-offline.spec.ts`, `e2e/report-from-error.spec.ts`, `e2e/my-reports.spec.ts` and `e2e/report-settled-alert.spec.ts`.

The trace pretends version 2 is live, Orderflow has switched as "What happens to Orderflow" (ticket 12) describes, and Abdul asks for this feature today. Version 1's issues 676 to 679 (the Mac script, the relay, the runbook and the risk-path refusal) are left out: they built the evening check's power to start fixes, and ticket 12 takes that power away at the switch, so the version 2 feature would not ask for them. That leaves ten change notes.

| Note | From v1 issue | What it does | Migration | Screens | Waits for |
|---|---|---|---|---|---|
| 01 | 666 | The `problem_reports` table, its row rules and two rights rows | 0076 | none | none |
| 02 | 667 | The header bubble, the sidebar item, the sheet, Send and the toast | none | every signed-in screen | 01 |
| 03 | 668 | A screenshot of the page behind the sheet, stored with the report | 0077 | every signed-in screen (the sheet) | 02 |
| 04 | 669 | One hint about the bubble for a first-time phone user | 0078 | every signed-in screen at 390 px | 02 |
| 05 | 670 | A report sent offline is kept and sent once | none | the sheet | 03 |
| 06 | 671 | The error page reports its own failure in one tap | none | error page | 02 |
| 07 | 672 | The My reports page and its row on the person card | none | My reports (new), person card | 01 |
| 08 | 673 | The evening check's own principal to read and settle reports | 0079 | none | 01 |
| 09 | 674 | An alert and a push when a report turns Fixed or Closed | 0080 | alerts list | 07, 08 |
| 10 | 675 | One route for the evening check, behind a secret of its own | none | none | 08 |

### The trace

Ticket numbers refer to `.scratch/workflow-v2/issues/`. "Decided by" names the ticket whose answer settles the step.

#### Before the feature: Orderflow as the switch left it

**0. The state Orderflow starts from.**
Who: nobody acts; this is what the switch sessions left behind.
What exists: `CLAUDE.md` with "Lane: careful", the five lane steps, a pointer to `docs/design.md`, "Change notes" in place of "Issue tracker", and a suite budget of 10 minutes (Orderflow's full run was 9.0 minutes on 31 October). `docs/design.md`, written by the brief session from `docs/patterns.md`, `docs/visual-direction.md` and the two ADRs. A screenshot baseline "from the live app that day". `.scratch/` gone from main, readable at the `v1` tag; the permission matrix that `tests/rights/matrix.test.ts` compares against moved into `tests/`.
Decided by: 12 (switch sessions, cleanup), 15 (core design for Orderflow), 16 (Orderflow's `CLAUDE.md`), 21 (suite budget).
**GAP C1.** The three named sources hold no screen list with routes and no module map (the drift research found "No written module map"), yet 24 needs every screen with its route and a baseline, and 22 takes `/tdd` seams from the modules part. Orderflow has no `toHaveScreenshot` test today, and none of ticket 12's four switch sessions is told to write one. "The live app" holds real orders, while the test suite runs on seed data.

#### The interview

**1. Abdul asks for the feature.**
Who: Abdul, in a Claude Code session in `~/code/orderflow`.
Reads: nothing yet. Writes: nothing yet.
The session judges the change too big for one session, so it is a feature of several notes, not a one-note `/goal` change.
Decided by: 08 ("A change too big for one session is cut into several notes"), 19 (definition of a feature).
**GAP C2.** No ticket names what runs the interview. `/build-feature` is a saved workflow whose script "judges nothing" and runs agents; it cannot hold a conversation. No skill is named for it (to-prd and to-issues retired), the one-page approval has no file path, and nothing says how the workflow knows the page was approved before it starts.

**2. Claude reads the code each note will touch.**
Who: the interview session.
Reads: `docs/design.md`, `CONTEXT.md`, the product brief, `src/app/(signed-in)/layout.tsx`, `src/controls/layout/shell-frame.tsx`, `src/model/rights.ts`, `src/lib/storage/*`, `src/model/alerts.ts`, `src/model/notifications.ts`, `src/app/(signed-in)/error.tsx`, `src/lib/db/pool.ts`.
Writes: nothing yet.
Decided by: 19 ("Claude writes all the notes of a feature in one interview, after reading the code each note touches").

**3. Claude cuts the feature into ten notes.**
Who: the interview session.
Writes: `changes/report-a-problem/01-the-problem-report-table.md` to `10-the-evening-check-route.md`, each half a page at most: what changes and why, a "Screens:" line, done checks as commands, risk classes, "Waits for:". Note 02 carries "Core design: adds the report bubble and the report sheet"; note 07 carries "Core design: adds the My reports screen at `/my-reports`", because adding a screen edits the screens part of `docs/design.md`.
Decided by: 08 (change note shape), 15 (the "Core design:" line; a shared pattern goes to one note and the others wait), 19 ("Waits for:"), 24 ("Screens:" line).

**4. No prototype for this feature.**
Who: the interview session decides; Abdul does not see one.
My reports is built from approved patterns (a list of rows, the person card), so it needs none. The bubble and the sheet are a new pattern but add no screen and do not rewrite the screens part, so no rule asks for one.
Decided by: 24 ("A new screen that needs a new pattern needs a prototype"), 15 (note check case 3 asks for a prototype only when the screens part is rewritten). Closed by plain reading, see the closed items below.

**5. Abdul approves one page.**
Who: Abdul, at the keyboard.
Reads: a line per note, the order, the "Waits for" graph, and the questions of four kinds:
- core-design changes: the bubble and sheet pattern (02), the My reports screen (07);
- migration direction: 0076 adds a table, 0077 adds a nullable column, 0078 adds the hint flag, 0079 adds a database role, 0080 adds an alert reason; all forward only;
- money or sign-in rules: the evening-check principal (08) and the route's secret (10);
- data out or a public contract: the `/api/evening-check` route (10), and the push payload that leaves through the phone's push service (09).
The new `html-to-image` dependency is not a question: the code rules' "No invented dependencies" check covers it. Orderflow's last full run sits under its 10-minute budget, so no budget question is added.
Writes: the approved page (location undefined, GAP C2).
Decided by: 19 (the four kinds), 21 (budget question only when over), 08 (migration direction waits for Abdul).
**GAP C3.** Note 01 adds two rights rows ("Problem report: send" and "My reports", every tick, own) and the row-level policies behind them. These are permission rules, not sign-in. No ticket says whether "sign-in rule" on the page and "authentication" among the risk classes cover who may read or write what. Version 1 put this exact choice to Abdul (ruling `q-rp1026-06`).

**6. Every done check is a command.**
Who: the interview session.
Writes: for 02 `npx playwright test e2e/report-a-problem.spec.ts`; for 07 `npx playwright test e2e/my-reports.spec.ts`; for 01 `npx vitest run tests/problem-reports/rights.test.ts`; and so on.
Decided by: 19 ("Every done check must be a command"), 24 (a note that names a screen carries an end-to-end done check).
**GAP C4.** No ticket says who writes the test code behind a done check. If the interview writes only the command, the spec file does not exist yet, the command fails on today's code for that reason alone, and the pre-run check accepts it; the implementer then writes its own check, against 24's premise that "the done checks are written in the interview, before the code exists". If the interview writes the specs, it is writing Playwright code against screens that do not exist, and nobody reviews it.

**7. The pre-run check.**
Who: a verifier, before the run starts.
Reads: each note's done checks. Runs each once on today's code.
Refuses: a check that already passes; a note with a "Screens:" line and no end-to-end done check.
Decided by: 19, 24.
GAP C4 continues: no ticket says whether this runs while Abdul is still at the keyboard (inside the interview) or after he has typed `/build-feature` and left. If a note is refused after he left, nothing says who rewrites it.

#### The run

**8. Abdul starts the run.**
Who: Abdul types `/build-feature report-a-problem`, optionally with `implementer=opus:medium`. His session runs the workflow script.
Writes: the feature branch from local main; `changes/report-a-problem/report.md` as the ledger. The run turns on keep-awake; Abdul keeps the lid open on power. A watchdog checks every 30 minutes.
Decided by: 19 (roles, models, parallel limits, state in git, long runs).

**9. Note 01 is built.**
Who: the implementer (Sonnet, high) in its own worktree.
Reads: note 01, `docs/design.md` (seams from the modules part), the existing `src/model/` files, Orderflow's `CLAUDE.md` facts (link `.env.local`, claim a database for the tree).
Writes, through `/tdd`: `tests/problem-reports/send.test.ts`, `read.test.ts`, `rights.test.ts`, `limit-outage.test.ts`; `supabase/migrations/0076_problem_reports.sql`; `src/model/problem-reports.ts`, `src/lib/problem-report-limit.ts`, `src/model/rights.ts` and the matrix input. Runs its own test files, then the red check before it hands over.
Decided by: 08, 16 (product facts stay in `CLAUDE.md`), 19 (do not wait for a seam), 21 (implementer runs its own files), 22 (test-first, red check).
**GAP C5.** The red check "puts back the source files from before the note" and runs the new tests. No ticket says whether a new migration counts as source, or how the test database is rebuilt from the old migrations. If 0076 stays, a test of the row rules (the rule lives in the migration's policies, per Orderflow's ADR 0001) can pass on the old app code, and the check refuses a sound test. If 0076 goes, the worker database has no table and every database test fails at load, which proves little.

**10. Note 01 is verified.**
Who: the verifier (Sonnet, high), in its own worktree, through the plugin's suite script.
Runs: note 01's done checks; `vitest related` on the diff; the source-text checks; the pattern and module checks (any failure prints a `DRIFT:` line); the red check again, which is the refusal. Note 01 names no screen, so no end-to-end spec, screenshot or hostile walk.
Writes: a pass or a reject report.
Decided by: 19, 21 (scoped run), 22 (red check at the verifier), 15 (`DRIFT:` lines), 24 (walk only for actions on screens).

**11. Note 01 is reviewed.**
Who: the reviewer (Opus, high), `/code-review` against the note and the core design. It runs after the verifier passes, so one attempt earns at most one strike.
Decided by: 08 (lane steps in order: tests, browser pass, then `/code-review`), 19. Closed by plain reading, see below.
The note touches a migration and writes to rows, but the per-note reviewer stays at high; the risk-class rubric at `max` belongs to the final reviewer (19).

**12. Note 01 merges into the feature branch.**
Who: the merger (Sonnet, medium).
Writes: the merge commit; note 01 "merged" in `report.md`.
The note check runs on the commit: no baseline changed, `docs/design.md` untouched, no route touched, so it passes.
Decided by: 19 (merger, ledger), 15 (note check cases).
**GAP C6.** The note check has no home. "How someone installs it" (10) ships four hooks, and the budget (14) starts at four; the note check is none of them. No ticket says whether it is a git hook in each product (Orderflow's `core.hooksPath` is empty today) or a Claude Code hook in the plugin, who installs it in Orderflow, or how it learns which note a commit belongs to.

**13. Notes 02, 07 and 08 start together.**
Who: three implementers, the limit for one feature.
Decided by: 19 (at most three notes at once; a note starts once every note it waits for has merged).

**14. Note 02: the bubble on every screen.**
Who: implementer, then verifier, then reviewer.
Writes: `src/controls/layout/report-bubble.tsx`, `src/app/(signed-in)/report-problem/actions.ts`, edits to `layout.tsx` and `shell-frame.tsx`, `tests/problem-reports/report-bubble.test.tsx`, `send-action.test.ts`, `e2e/report-a-problem.spec.ts`, and the new pattern in `docs/design.md` with a check that refuses a second report entry point.
The verifier runs the end-to-end specs and screenshots of the screens the note changes, then the hostile walk: reload with the sheet open, two fast taps on Send, Command and Enter, the 390-pixel width, an empty box, a failed send.
Decided by: 15 (a pattern entry names its check; note check case 2 accepts because note 02 has the "Core design:" line), 21, 24.
**GAP C7.** The bubble changes every signed-in screen, so every baseline that the verifier compares now differs, and "any difference fails". No ticket says who writes the new baselines for a screen a note changes on purpose, at which step, or whether Abdul approves a changed baseline as he approves a new one. If the implementer updates them, the screenshot test cannot catch drift on any screen the note names. A second part: note 02 edits the route group's shared `layout.tsx`. No ticket says whether that counts as touching every route for the note check's "Screens:" rule, so note 02 may have to name about thirty screens.

**15. Note 07: My reports, a new screen.**
Who: implementer, verifier, reviewer, merger.
Writes: `src/app/(signed-in)/my-reports/page.tsx`, `loading.tsx`, `address.ts`; edits to `shell-frame.tsx` and `src/model/shell.ts`; `tests/problem-reports/my-reports-page.test.tsx`, `my-reports-row.test.tsx`; `e2e/my-reports.spec.ts`; the screen and its route in the screens part of `docs/design.md`.
The new screen has no baseline yet; the final verifier takes its first one.
Decided by: 24 (new screen from approved patterns, first screenshot becomes its baseline at the final check).

**16. Note 08: the evening check's principal.**
Who: implementer, verifier, reviewer, merger.
Writes: `supabase/migrations/0079_evening_check.sql` (a database role), `src/lib/db/evening-check.ts`, `src/model/problem-report-outcomes.ts`, `tests/problem-reports/evening-check-connection.test.ts`, `evening-check-hostile-owner.test.ts`, `outcomes.test.ts`.
The role's password is a production secret. Setting it is Abdul's step, written under "Do" in `~/.claude/pending.md`.
Decided by: 16 ("Do" holds actions), 19.

**17. Notes 03, 04 and 06 start once 02 merges.**
Who: three implementers in parallel.
**GAP C8.** Notes 03 and 04 each add a migration, and both run at once. Each worktree sees 0076 as the last file, so both name their file 0077. The file names differ (`0077_problem_report_screenshot.sql`, `0077_report_hint.sql`), so git merges both without a conflict and the merger sees nothing to count as a strike. Orderflow's own rule ("each number is claimed at build time") points at version 1's issue-tracker doc. No version 2 ticket says how parallel notes claim a migration number, or that notes with migrations wait for each other.

**18. Note 03, attempt 1: strike one.**
Who: implementer, then verifier.
Writes: `report-bubble.tsx` changes, `src/lib/storage/upload-*.ts`, `0077_problem_report_screenshot.sql`, `tests/problem-reports/screenshot-send.test.ts`, `report-screenshot.test.tsx`, `draw-the-page.test.ts`.
The verifier's walk scrolls Home to 1,500 px, opens the sheet, and the screenshot shows the top of the page. Reject: strike one. The failing walk case goes into the reject report, and the next implementer commits it as a spec.
Decided by: 24 (walk, a reject is a strike, a fault case stays as a spec), 19 (strikes). This is version 1's `668-attempt-2-verify.md`.

**19. Note 03, attempt 2: strike two.**
Who: a fresh implementer with the reject report, then verifier and reviewer.
The verifier passes; the reviewer reads `viewportShift` and finds the drawn copy still starts at the page top, because the browser cases check only the fixed bar. Reject: strike two.
Decided by: 19, 08 (order).

**20. The note checker corrects note 03.**
Who: the note checker (Opus, high), fresh.
Reads: note 03, both failure reports, the code.
Finds: the done check graded an unscrolled Home, where every wrong build passes. A scrolled case stays inside what Abdul approved, so it corrects the check, records the change in the report, and starts a third attempt, which is not a strike.
Decided by: 19 (strike two, one correction per note).

**21. Note 03, attempt 3: the note fails.**
Who: a fresh implementer, then verifier and reviewer.
The reviewer finds that Remove stays live while Send is on its way: a tap removes the thumbnail, the toast says "Sent", and the picture is still uploaded and stored. Reject. That is the third failure: note 03 fails, its branch stays, note 05 (which waits for 03) does not start, and the rest carry on. The default "the screenshot undoes the window's scroll only, not a scroll inside the page" is reversible, so it goes in the end report, not under "Decide".
Decided by: 19 (third failure, dependants wait), 16 ("Decide" only for defaults hard to undo).

**22. Notes 04, 06, 09 and 10 finish.**
Who: implementers, verifiers, reviewers, merger.
Note 09 writes `0080_report_alert.sql`, `src/model/alerts.ts`, `src/model/notifications.ts`, `tests/problem-reports/report-alert.test.ts`, `e2e/report-settled-alert.spec.ts`. Note 10 writes `src/app/api/evening-check/route.ts` and `tests/evening-check/route.test.ts`; its secret is another "Do" item for Abdul.
Decided by: 19.

**23. The run stops short.**
Who: the starting session.
Writes: `report.md` (8 merged, 1 failed, 1 not started, defaults taken, time and tokens); a phone notification such as "report-a-problem: 8 of 10 notes merged, 1 failed, 1 not started".
The feature does not merge to local main, because not every note passed.
Decided by: 19 ("The feature merges to local main only when every note and the final check pass").
**GAP C9.** Nothing says what happens next. 19 says typing `/build-feature report-a-problem` again "skips the merged notes and carries on", but not whether a failed note retries, with fresh strikes or none; who changes the note (version 1 carved the Remove control out, and version 2 has no carve); whether a changed note needs Abdul's approval again; or whether the final check runs on the eight notes that merged.

**24. Abdul decides about note 03 and starts again.**
Who: Abdul. Under GAP C9 the step has no owner; the trace assumes he drops Remove for now, as version 1 did, and types `/build-feature report-a-problem` again.
Reads: `report.md`, branch state. Note 03 passes; note 05 starts, passes and merges.
Decided by: 19 (re-run from the report), otherwise GAP C9.

**25. The final verifier.**
Who: the final verifier (Sonnet, high), through the suite script, holding the machine lock.
Runs on the feature branch: `npm test`, `npm run test:harness`, the typecheck, every end-to-end spec, every baseline screenshot. Takes My reports' first screenshots at 390 and 1280 px as its new baseline. Writes the full-run time into `report.md` against the 10-minute budget.
Decided by: 19, 21 (full suite only here, one lock), 24 (new baseline at the final check), 15.
**GAP C10.** The run took days, and local main moved meanwhile (for example, a one-note fix Abdul asked for from the evening check's sorted reports). The final check tests the feature branch alone; the merger then merges into a different main. No ticket says whether the feature branch takes main in before the final check.

**26. The final reviewer.**
Who: the final reviewer (Opus, xhigh), `/code-review` at `max` with the money, sign-in and secrets rubric, because the feature touches migrations, row writes and secrets.
Reads: the whole feature diff, the brief, `docs/design.md`, all ten notes.
It finds, as version 1's critical gate did, that `sendProblemReport` names `screenshot_file` in every insert, so the code breaks every report if it reaches production before 0077. A fresh implementer fixes the findings in one round, and both final agents run again.
Decided by: 19 (final check, one fix round).
**GAP C11.** The fix round sits outside the red check and the hostile walk. The red check runs at the implementer's handover and in the per-note verifier's scoped run; the final verifier runs neither. No ticket says what "the code from before the note" means for a fix round, or whether its new tests must fail first.

**27. The merger merges the feature into local main.**
Who: the merger.
Writes: the merge commit, My reports' baseline committed with the feature, `report.md` with the screens section (new screen at 390 and 1280 px; every changed screen before and after). The session-start hook now prints "Pending: 2 to do, N to decide".
Decided by: 19, 24, 16.

#### After the merge: Abdul's side

**28. The pre-launch gate, steps 1 to 7.**
Who: "an agent", on the feature branch, "before the push".
**GAP C12.** None of the seven roles runs it, and no ticket places it before or after the merge to local main. If it runs after, a failed row finds the feature already on main with no step to take it off. Step 1 checks row rules, and Orderflow last ran it against production (its `docs/launch.md`), where 0076 to 0080 do not exist yet. Decided closest by: 19, 08, the code rules' gate.

**29. Abdul reads the report and approves the screens.**
Who: Abdul.
Reads: `report.md`, its screens section, the "Decide" entries in `~/.claude/pending.md`.
If he dislikes My reports, a follow-up note changes it and the note check sees a changed baseline the note names.
Decided by: 24 ("Abdul looks at it in the feature report before the push, which is already his step"). Closed by plain reading.

**30. The migrations reach production.**
Who: undecided.
Orderflow applies migrations by `supabase db push` by hand (its `docs/launch.md`, row 10). 0076 to 0080 must go in order and before the code, or every report fails.
**GAP C13.** Version 2 approves a migration's direction in the interview (08, 19) but no ticket says who applies it to production, when, or in what order against the push that deploys the code. Ticket 12 gave Abdul that job for version 1 only ("he applies the migrations").

**31. Abdul does the "Do" items.**
Who: Abdul.
Writes: the evening-check principal's password and the route's secret, in Supabase and Vercel.
Decided by: 16 (pending file "Do" items).

**32. Abdul pushes to origin.**
Who: Abdul, always. `git push origin main`; Vercel deploys.
Decided by: global `CLAUDE.md` (push only when Abdul says so), 19 ("The push stays his").

**33. The audit picks it up.**
Who: the weekly desktop task's script, then the brainstorm page on the 1st.
Reads: session transcripts, `report.md` figures, `DRIFT:` lines, the flake ledger. Writes: a summary to `roufmlp/ideas`; rows for cost, tokens, strikes per role, interruptions and drift.
Decided by: 14, 19 (per-role figures in the report), 21 (flake row).

### Gap detail, case 2

1. **C1. Where Orderflow's core design comes from** (step 0). The sources ticket 12 names (`docs/patterns.md`, `docs/visual-direction.md`, two ADRs) hold no screen list with routes and no module map. Ticket 24 needs both, and 22 takes `/tdd` seams from the modules part. Orderflow has no screenshot test, no switch session is told to write one, and "the live app" holds real orders while tests run on seed data. Closest: 12, 15, 22, 24. Needs Abdul's call.

2. **C2. What runs the interview** (steps 1 and 5). No command or skill is named for the interview that writes the notes and the one-page approval. The workflow script cannot hold a conversation, the approved page has no path, and nothing tells the workflow it was approved. Closest: 08, 19. Needs Abdul's call, since a new skill counts against the plugin budget.

3. **C3. Whether permission rules count as sign-in rules** (step 5). Note 01's rights rows and row policies decide who may read whose reports. No ticket says whether the page's "sign-in rule" question and the "authentication" risk class cover them. Closest: 08, 18, 19. Needs Abdul's call, one line.

4. **C4. Who writes the test behind a done check, and when the pre-run check runs** (steps 6 and 7). A command naming a spec that does not exist yet fails on today's code and passes the refusal, so the implementer ends up writing its own done check. Nothing says whether the pre-run check runs while Abdul is still at the keyboard, or who fixes a refused note after he leaves. Closest: 19, 22, 24. Needs Abdul's call.

5. **C5. The red check and migrations** (step 9). The check restores "the source files from before the note", but no ticket says whether a new migration counts as source or how the test database is rebuilt. If the migration stays, a row-rule test passes on the old code and is refused; if it goes, every database test fails at load. Closest: 22. Needs Abdul's call, or a fact once the build tries both.

6. **C6. The note check's home** (step 12). The plugin ships four hooks and the budget starts at four; the note check is not one of them. Git hook or Claude Code hook, who installs it in Orderflow (whose `core.hooksPath` is empty), and how it maps a commit to its note are all unstated. Closest: 10, 14, 15, 22, 24. Needs Abdul's call.

7. **C7. Baselines for screens a note changes on purpose** (step 14). Note 02 changes every signed-in screen, and "any difference fails". No ticket says who writes the new baselines, at which step, or whether Abdul approves changed ones as he approves new ones. Nor does any say whether an edit to the shared `(signed-in)/layout.tsx` counts as touching every route for the "Screens:" rule. Closest: 15, 21, 24. Needs Abdul's call.

8. **C8. Migration numbers in parallel notes** (step 17). Two notes running at once both take 0077 under different file names; git merges both cleanly and no strike fires. No ticket says how a note claims a number, or that notes with migrations wait for each other. Closest: 15, 19. Needs Abdul's call; "a note with a migration waits for every earlier note with one" would close it.

9. **C9. After a note fails three times** (steps 23 and 24). Re-running `/build-feature` skips merged notes, but nothing says whether a failed note retries or with how many strikes, who rewrites it, whether Abdul approves the rewrite, or whether the final check runs on the notes that did merge. Version 1's carve has no successor. Closest: 19. Needs Abdul's call.

10. **C10. The final check against a main that moved** (step 25). A run of days meets new commits on local main. The final check tests the feature branch alone, then the merger merges into a different main. Closest: 19. Needs Abdul's call; small.

11. **C11. The final fix round skips the red check and the walk** (step 26). The fresh implementer that fixes final-check findings has no "before the note" to test against, and the final verifier runs neither check. Closest: 19, 22, 24. Needs a default; low stakes.

12. **C12. Who runs the pre-launch gate, and when** (step 28). "An agent" runs steps 1 to 7 "before the push", but none of the seven roles owns it. It has no place before or after the merge to local main, a fail after the merge has no road back, and step 1 was last run against production, where the new migrations do not exist yet. Closest: 08, 19, the code rules' gate. Needs Abdul's call.

13. **C13. Who applies migrations to production, and in what order** (step 30). The interview approves each migration's direction, but no ticket says who runs `supabase db push`, when, or that migrations go in before the push that deploys the code. Version 1 put that on Abdul (ticket 12), and its gate caught the order fault on 0077. Closest: 08, 12, 19. Needs Abdul's call; this is the step a deploy cannot roll back.

#### Closed by plain reading

- **Verifier before reviewer, one strike per attempt** (step 11). 08 lists the lane steps in order: "3. Tests and typecheck. 4. A browser pass through the main flow. 5. One `/code-review` in a fresh context." The reviewer runs only after the verifier passes, so an attempt earns one strike at most.
- **Baseline approval before the push** (step 29). 24: "Abdul looks at it in the feature report before the push, which is already his step." The push is his own act, so it is the approval; nothing more is needed.
- **No prototype for a new pattern that adds no screen** (step 4). 24: "A new screen that needs a new pattern needs a prototype"; 15 asks for one only when a note "rewrites the screens part". The bubble is a new pattern on existing screens, so Abdul approves it from a "Core design: adds ..." line without seeing it. That follows from the text; whether he wants it is another matter.
