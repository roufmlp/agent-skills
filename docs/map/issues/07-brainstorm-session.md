Status: resolved
Assignee: Abdul (wayfinder session 2026-10-27)
Type: grilling
Blocked by: 05

# How the brainstorm session works

## Question

What happens in the session that picks the next product? Pin down how often it runs (every two weeks at the soonest, monthly at the latest) and what starts it; where ideas come from (Abdul's own list, problems from his work, trends the agent researches); what Abdul receives before it; how it ends, which should be one chosen idea and its one-page brief; and where the record of past ideas lives so the session never repeats itself. The session also gives each MVP that is not yet a product one result, graduate, keep or stop, as "What moves an MVP to the careful lane" set out.

## Answer

The brainstorm session runs on the 1st and the 15th of each month. Monthly would give one new MVP a month, too slow for a product every two to four weeks when an MVP takes four days at most. Abdul can also start one at any time.

A cloud routine starts it. The routine prepares a one-page agenda, and Abdul opens that same session from claude.ai/code/routines and carries on. The laptop can be shut. Nobody has confirmed the routine sends a notice when a run finishes, so the first run tests that; if it sends nothing, a calendar event on the same dates does the job. A run that finds last time's session still unopened updates that page rather than making a second one, and an unopened session does not use up any MVP's one keep.

Everything the session reads and writes lives in a small private GitHub repo, `roufmlp/ideas`. The routine needs a GitHub repo because it starts from a fresh clone, and this skills repo is going public, so the ideas cannot live here. The ideas repo holds two things:

- The idea log: every idea, its status and the reason for each "no". A rejected idea comes back only with a new reason.
- The MVP list: every open MVP, its age and its keep count. Whichever session changes an MVP (done, graduated, stopped) updates its line. The routine does not clone MVP repos to rebuild the list.

Ideas come from Abdul first. He adds one to the log at any time in a single line. Problems from his own work count too. Before each session the agent adds at most three researched ideas, each with a source.

The page Abdul gets has two parts, in this order. First the open MVPs, each with its age and a suggested result. Then a shortlist of at most five ideas, each with the problem, who has it, the main flow in one line and a rough size. The agent ranks the shortlist and names its first choice with one reason.

The session runs in the same order. The MVP review comes first: Abdul gives each open MVP graduate, keep or stop, as "What moves an MVP to the careful lane" set out. Stopping one frees time; graduating one may fill the cycle with careful-lane work instead of a new idea. Then Abdul picks at most one idea. "No pick" is a valid result, and the log records why.

A picked idea leaves the session with a draft brief, its prototype link empty. The draft sits in the ideas repo until the prototype session creates the MVP's own repo, then moves there, and the log links to it. The brief is finished when Abdul approves the prototype, as "What the fast lane does, from brief to done" requires.

`CONTEXT.md` now defines brainstorm session and idea log.

Later: "What the careful lane keeps" adds open change notes from parallel-hunt to the page, under each product, as one line each in the ideas repo.

Later: "What happens to procurement and the other chain work" parks procurement until this session picks its revamp. The revamp goes into the idea log as an idea, and the page lists each parked product by name.

Changed by "How the ideas repo and the brainstorm routine run" (2026-11-01): the page is a file, `pages/YYYY-MM-DD.md` in the ideas repo, and the session marks it `Opened:` on its first reply to Abdul, which is how the next run knows. The routine's prompt lives in the repo as `routine.md`. Every writer pushes to the ideas repo without asking, since the repo is exempt from the push rule.

Changed by "How an MVP's limits and its end are recorded" (2026-11-01): keep has no limit, and the page shows each MVP's age. Every line on the MVP list, a client's site included, starts the day its brief is first written.
