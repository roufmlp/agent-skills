Status: resolved
Type: grilling
Blocked by: 08, 17

# How a regular audit keeps the workflow small

## Question

What session audits the workflow every so often, so it stops growing a little each day and drifting from what Abdul agreed? Pin down how often it runs and whether it shares a schedule with the brainstorm session; what it measures (time from idea to done, skills and hooks nobody used since the last audit, rules that never fired, lines added since last time); what it may do on its own and what it brings to Abdul; and whether a hard budget (a cap on skills, hooks or total lines) refuses growth between audits, so the audit is a backstop rather than the only guard. "How the brainstorm session works" settled that session as a cloud routine on the 1st and 15th of each month, reading a private `roufmlp/ideas` repo. "What the careful lane keeps" set the starting size: 23 skills and 6 hooks. "How the README tells the version story" puts a version 2 cost per shipped feature in the README's first-screen table once three products have graduated, measured the same way as the version 1 figure from "What version 1 cost, and where its time went". The audit decides who measures it and when.

Changed by "What version 1 cost, and where its time went" (2026-10-30): the version 1 figure is run hours per shipped issue, 69.4 minutes across version 1 and 68.7 for Orderflow, read from each run's main-session wall clock. It covers the build loop only. In Orderflow's window, 53% of the commits landed outside every run session, and no record says how long that work took. The research file's last section measures version 2 the same way: build sessions only, each transcript's first line to its last, divided by features whose commit reached main. Three things are this ticket's to settle. What a version 2 feature is, since a version 1 issue was one slice whose loop took a median of 35 minutes. Whether the comparison covers the whole pipeline, where version 2 cuts most; that needs a script over the version 1 transcripts for the work outside the runs. And when the measuring happens, because Claude Code's documented default deletes transcripts after 30 days.

## Answer

The audit is a monthly table on the brainstorm page, built from a weekly summary, and a budget in the push check refuses growth between audits. The audit measures and proposes. It never removes anything.

**Where and when.** The brainstorm routine runs in the cloud from a fresh clone and cannot read the session transcripts on the laptop, so the measuring runs locally. A desktop scheduled task runs a script every Sunday. The script summarises each session it has not summarised yet, a few KB per week, and pushes the summary to `roufmlp/ideas`. A run missed while the laptop sleeps fires once on waking. Because the summaries hold what the audit needs, the transcripts can go after 30 days. On the 1st of each month the brainstorm page gets a third part, after the open MVPs and the ideas: the audit table, then one line per proposal. It runs on the 1st only, since the workflow does not grow much in two weeks.

**What it measures.** One row per measure, with columns for this month, last month and version 1. About half a page.

| Row | What it counts |
|---|---|
| Cost | Build-session hours per shipped change note; bug-fix sessions as a second figure, as version 1's 76.5 minutes is |
| Tokens | Tokens and list-price dollars per change note, by model; version 1's known figure is $20 to $23 per issue for subagents alone |
| Speed | Days from idea to live for each MVP that went live, from the ideas repo |
| Decisions | Questions sessions put to Abdul, per change note and per brief, found by the question tool and the ❓ marker |
| Interruptions | Count, hours lost and cause: usage limit, permission prompt, a question to Abdul, an error, a crash or restart, laptop sleep |
| Bugs | Bugs found after a note reached main: fix commits for that note and bugs parallel-hunt confirms |
| Parallel | Most sessions running at once, and each feature's elapsed days against its session hours |
| Drift | Failures of the check "How the careful lane keeps every slice aligned to the core design" chooses |
| Not used | Skills and agents no session used since the last audit |
| Growth | Every skill, agent and hook added or removed, by name, against the budget; lines in the private CLAUDE.md and memory |

A version 2 feature is one change note whose commit reached main. It is the nearest match to a version 1 issue, since both are one session's loop. An MVP adds the idea-to-live days.

An interruption starts when nothing in an unfinished session writes for 30 minutes: not the main session, not any subagent, and no command still running. A subagent writes its own transcript file and a long test run leaves its command open, so neither counts. Abdul cares about one case above all: he starts a two-day or three-day run, comes back, and finds it waited on something after the first hour. The row names the cause so it can be fixed before the next long run.

"Rules that never fired" is left out. A transcript cannot show whether a written rule changed anything.

**What it may do.** It proposes and Abdul answers yes or no in the session, for example "retire grill-me: not used in two audits". A hook is never proposed for retirement just because it did not fire, since a refusal hook is right to stay silent until something unsafe happens. Its row shows the refusal count instead.

**The budget.** A budget file in `agent-skills` sets the plugin's limits, and the push check from "How someone installs it" refuses a push that goes past them. The limits start at the plugin's counts on the day of the switch, today four skills of Abdul's own, seven agents and four hooks, plus a line limit on his skill files set at the switch. The limit does not forbid growth. Adding a skill, agent or hook raises its number in the same commit, and an agent changes the budget file only with Abdul's approval, as with the `commit-msg` hook. CLAUDE.md, memory and the two private hooks sit outside the repo, so only the audit counts them.

**The README figure.** Once the third product graduates, the audit proposes the line: "add the version 2 cost to the README: N minutes per change note, against 69". Abdul approves it and that session edits the README.

**The version 1 baseline.** Version 2 cuts most of its time outside the build loop, so comparing build loops alone would hide most of the cut. One script reads the version 1 transcripts once, as a task in the build after this map. It measures the work outside the runs, plus the decisions, tokens and interruptions the table compares, with the decisions counted from the queue files. To keep those transcripts until it runs, `cleanupPeriodDays` in `~/.claude/settings.json` went from the 30-day default to 90 on 2026-10-31, with Abdul's approval. That holds roughly 8 to 20 GB more at September and October's rates, against 95 GB free; the weekly cleanup job touches only caches, not the transcripts. Once the script has run, the setting goes back to 30.

**Handed on.** How the notes of one feature run in parallel without Abdul goes to "How a feature with several change notes runs without Abdul". What stops two agents building the same thing two ways goes to "How the careful lane keeps every slice aligned to the core design". An agent that takes Abdul's decisions from his preferences is out of scope; it waits until three audits show the decision count.

`CONTEXT.md` now defines audit and interruption.

Changed by "How the careful lane keeps every slice aligned to the core design" (2026-10-31): the Drift row counts the fixed `DRIFT:` lines that the screen, pattern and module checks print when they fail in a build session, so a failure counts even when the check blocks the merge.

Changed by "How a feature with several change notes runs without Abdul" (2026-10-31): the budget now counts workflows beside skills, agents and hooks, starting with `build-feature` and its seven agent files. Each feature's report records model, effort, tokens, cost and strikes per agent role, so the Tokens row compares settings month by month, and after three audits the audit proposes the permanent model and effort for each role.

Changed by "How the ideas repo and the brainstorm routine run" (2026-11-01): the audit table goes to its own file, `pages/YYYY-MM-DD-audit.md`, and the brainstorm page keeps one line linking to it plus one line per proposal. The weekly script pushes to the ideas repo without asking, from the clone at `~/code/ideas`.

Changed by "How an MVP's limits and its end are recorded" (2026-11-01): the push check also refuses a `SKILL.md` or agent file that contains a date, "ruled" or "changed by". The line limit on skill files is still set at the switch.

Changed by "How every version 2 session stays under 300k tokens" (2026-11-02): the Tokens row also shows each role's largest context, its compactions and its median start size. When a role compacts in more than one run in ten, the audit proposes a fix, such as smaller notes. When start sizes fall, it asks on the page whether to lower the compaction window from 400k to 300k.
