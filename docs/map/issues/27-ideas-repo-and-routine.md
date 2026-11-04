Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: grilling
Blocked by: 25

# How the ideas repo and the brainstorm routine run

## Question

"How the brainstorm session works" put the idea log and the MVP list in a private `roufmlp/ideas` repo, and the session in a cloud routine on the 1st and 15th. Tracing an MVP through it in [the walkthrough](../research/25-walkthrough.md) found four holes, gaps F1 to F4.

No ticket creates the repo or gives its files a layout, yet the audit's Speed row needs an idea date and a live date from it. The cloud session starts from a fresh clone with none of `~/.claude/`: no brief template, no grilling skill, no writing rules, no ASD-STE100 rule, and the routine's prompt has no home. Copying the writing rules in would break "no other copy" from "Which steering files each lane loads". Nothing says where the page lives or how a run tells that the last session went unopened, and that decides whether a keep is spent. On the 1st the audit table can push the page past one page. Last, the weekly script, the routine, the brainstorm session and build sessions all write to the repo, while the global rule makes every push Abdul's call, and a routine's output lands on `claude/` branches that the next fresh clone does not see.

Decide who creates the repo and when, where the routine's prompt and the cloud session's rules come from, how a run knows a session went unopened, and whether writes to the ideas repo are exempt from the push rule.

The lighter option: the ideas repo ships nothing, so pushes to its default branch are exempt; the routine's prompt lives in the repo; the session writes a status file when Abdul opens it. A heavier answer says what this would cost.

Changed by "Whether version 2 is built in two stages" (2026-11-01): this ticket is part of stage one, the fast lane, and stage one ends only when it is resolved. An MVP waiting only for stage two stays at keep without spending its one keep, and the brainstorm page lists it as "waiting for the careful lane".

## Answer

The ideas repo is a private repo that every writer pushes to straight, outside the push rule. The routine follows a prompt kept in that repo, and the page records when Abdul opens it. Abdul accepted every recommendation on 2026-11-01.

**Who creates it.** The stage-one build session creates `roufmlp/ideas` with `gh repo create --private` and writes its first files. It also creates the routine with the `schedule` skill: cron `0 9 1,15 * *`, the ideas repo and `agent-skills` attached, and a one-line prompt, "Follow `routine.md`." Abdul approves each of those two steps in that session. The first run still has to show whether the cron field takes `1,15` and whether a finished run tells Abdul; the current docs say neither. If no notice comes, the calendar event from "How the brainstorm session works" stands in.

**The layout.**

- `ideas.md`: the idea log, one line per idea with its date, status and reason.
- `mvps.md`: the MVP list, one line per MVP with its repo, idea date, live date, age, keep count and result. The audit's Speed row reads its two dates here. "How an MVP's limits and its end are recorded" settles the exact fields.
- `notes.md`: the open change-note lines from parallel-hunt and the parked products.
- `audit/YYYY-Www.md`: one weekly summary from the audit script.
- `pages/YYYY-MM-DD.md`: one brainstorm page per run.
- `briefs/<name>.md`: a draft brief until its MVP's repo exists.
- `routine.md`: everything the routine does, so a change to it is a commit with history.
- `CLAUDE.md`: the rules for any session in this repo.

The local clone lives at `~/code/ideas`, and the fast-lane `CLAUDE.md` template names that path, since the audit script and build sessions write from the laptop.

**Pushes.** Pushes to `roufmlp/ideas` are exempt from the push rule, and one line in the global `CLAUDE.md` says so. The repo is private and ships nothing to anyone, so a bad push costs one revert, while the rule would stop the routine and the audit script from finishing at all. A routine pushes to a `claude/` branch only when its prompt names no other, so `routine.md` names `main`. The `commit-msg` hook from "One repo that is safe to publish" does not run here, because this repo is where client names belong. Each writer runs `git pull --rebase` before it pushes and retries once. Every file has one writer or only gains lines, so the rebase is nearly always clean. A second failure goes to the pending file, and the writer stops.

**The page, and an unopened session.** The routine writes the page to `pages/YYYY-MM-DD.md`, pushes it and shows it as its first reply. The first reply the session makes to Abdul writes `Opened: <date>` at the top of that file and pushes it. The next run reads the last page. With the line, it writes a new page. Without it, it updates the old one and counts no keep and no age against any MVP. This needs nothing beyond git.

**The 1st of the month.** The audit table goes to `pages/YYYY-MM-DD-audit.md`. The page keeps one line linking to it and one line per proposal, so it stays one page. The proposals need Abdul's yes or no; the table is evidence he opens only when a proposal is unclear.

**What the cloud session reads.** A cloud session does not install plugins from a repo's settings, but it does read the repo's `CLAUDE.md` and `.claude/skills/`, and it clones every attached repo. So `routine.md` reads the brief template from the `release` branch of the attached `agent-skills` clone, the same version friends and the Copilot app get, and no second copy exists. The session needs no grilling skill: the template lists its fields, and the session asks Abdul for each empty one with a recommended answer. The prototype session runs on the laptop and has grilling if the brief needs more. The ideas repo's `CLAUDE.md` holds one line, "Reply to Abdul in ASD-STE100 Simplified Technical English". That repeats a rule, but one line is too short to drift. The writing rules stay out of the cloud. The page follows a fixed form set in `routine.md`, and the prototype session edits the draft brief with `writingrules`. The cost is that Abdul reads the page and the draft brief once without the writing rules applied.

**What was turned down.** Keeping the push rule for this repo: the next run would never see the last run's work. The prompt in the routine's settings on claude.ai: no history and no copy in git. Moving `writingrules` into the ideas repo with a link from `~/.claude/skills/`: one copy in both places, but a link to keep alive and a push before the cloud sees any edit. Copying both rules in: "Which steering files each lane loads" already refused a second copy.

Facts from the current Claude Code docs, checked 2026-11-01: routines (code.claude.com/docs/en/routines.md), cloud environments and what carries over (code.claude.com/docs/en/cloud-environments.md). Notes in `research/27-routine-facts.md`.

`CONTEXT.md` now defines brainstorm page, and the audit entry says its table sits beside the page.

Changed by "How an MVP's limits and its end are recorded" (2026-11-01): the fields of `mvps.md` are name, repo, type (`site` or `app`), for, start date, live date, done date and result.
