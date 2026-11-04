Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: grilling
Blocked by: 10, 15, 21

# Which stacks the lanes support

## Question

The test and alignment decisions name Orderflow's tools. The verifier's scoped run is `vitest related`, the screenshot test is Playwright's `toHaveScreenshot`, module rules are ESLint's `no-restricted-imports`, and step 10 of the pre-launch gate is the Supabase production checklist. At work Abdul builds in C# and .NET with Angular and MS SQL.

Decide first whether the lanes cover a stack other than Next.js on Supabase at all: Abdul's own products only, or work projects too. The destination brings only the toolbox to work, so a yes widens it, and the answer has to say so.

If the lanes do cover other stacks, decide what fills each slot that names a tool. Angular can likely keep Playwright and ESLint. The .NET side needs:

- the test command the product's `CLAUDE.md` names, and how the verifier scopes a run to the note's diff, since `dotnet test` filters by name and has no change-based selection built in that matches `vitest related`;
- a module rule tool in place of ESLint, with ArchUnitNET and NetArchTest as the candidates to check;
- a database step in the pre-launch gate for MS SQL in place of the Supabase checklist, and how a migration's direction reaches Abdul when the migrations come from Entity Framework.

"How someone installs it" found that the Copilot app at work takes the plugin's skills and agents but no hooks. Nobody has checked whether it runs a saved Claude Code workflow such as `/build-feature`. If work projects are in, the answer hangs on that fact, and a research ticket should settle it first.

The lighter option is to keep the lanes on Next.js and Supabase, and to let the toolbox alone go to work. An answer heavier than that says what the lighter one would cost.

## Answer

The lanes cover Abdul's own products only, and version 2 names the Next.js and Supabase tools directly. Work gets the toolbox through the Copilot app, as "How someone installs it" decided, and Abdul adapts it on his work laptop after the install. He works differently there, and the Copilot app takes no hooks, so a careful lane at work would lose the red check and the note check hook and keep only reminders. The destination stays as it is.

**No slots now.** Every product so far runs on Next.js and Supabase. Reading each tool from the product's `CLAUDE.md` would add a layer to the suite script and the gate for a stack that does not exist yet.

**A port list instead.** The spec carries one table. Each row names a tool slot, its value today and the place in the plugin that uses it:

| Slot | Today | Used in |
|---|---|---|
| Scoped test run | `vitest related` | the suite script, for the verifier's run |
| Red check | vitest, by test name | the suite script and the note check hook |
| Screenshot test | Playwright's `toHaveScreenshot` | the core design's screen checks |
| Module rule | ESLint's `no-restricted-imports` | the core design's module checks |
| Database step | the Supabase production checklist | step 10 of the pre-launch gate |

Adding a stack means filling a new column and changing only those places. Porting is a known list of jobs, not a search through the plugin.

**When the port happens.** An MVP can use any stack from day one, because the fast lane needs almost none of these tools. The port happens only when an MVP on a new stack graduates, in the session that writes its core design. If the MVP stops, the port never costs anything.

**Stack choice.** No new rule and no new line in the brief. Abdul worried that agents would offer only Next.js because the workflow supports it. With the port list and the port at graduation, the workflow gives no reason to prefer a stack, and he can push for other options when he wants them.

**What was left out.** The .NET tool choices (a scoped `dotnet test` run, ArchUnitNET or NetArchTest, an MS SQL step for the gate and Entity Framework migrations) and the research ticket on whether Copilot runs `/build-feature`. Both mattered only if work projects were in.

**What the lighter option would cost.** This is the lighter option, plus one table.

`CONTEXT.md` now defines port list.
