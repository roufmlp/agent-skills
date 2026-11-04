Status: resolved
Assignee: Abdul (wayfinder session 2026-10-27)
Type: grilling
Blocked by: 01, 03, 04, 13

# What the careful lane keeps

## Question

When a product graduates, what process does it go through? Two directions are on the table. One keeps today's chain whole: to-prd, to-issues, harden-issues, run-issues, parallel-hunt and all 33 hooks. The other keeps a lean set (the security rules, a test suite, parallel-hunt and the pre-launch gate) and retires the rest to the version 1 record. Decide which skills and hooks stay, which retire, and which the fast lane uses too.

## Answer

A product's changes go through the fast lane's loop with more checks added. The chain does not survive. Issue files, to-prd, to-issues, harden-issues, run-issues and the decisions queue go to the version 1 record. Orderflow is the reason: 728 issue files and 2,528 commits in six weeks, and still half done. Built-in tools now do most of what run-issues did, as "What recent Claude Code features and Anthropic posts can replace" found.

The unit of work is a change note. Claude interviews Abdul and writes it, in half a page at most: what changes and why, which screens or flow it touches, the done checks, and which risk classes it touches. It lives in the product's repo, for example `changes/03-csv-export.md`. It is the brief made smaller, so Abdul reads one shape in both lanes. A change too big for one session is cut into several notes. Keeping those notes in line with each other belongs to "How the careful lane keeps every slice aligned to the core design".

Every change passes five lane steps before it is done:

1. The change note.
2. One auto-mode session, with `/goal` set to the note's checks.
3. Tests and typecheck.
4. A browser pass through the main flow.
5. One `/code-review` in a fresh context.

The risk classes are the five from the direct road: money, authentication, secrets, migrations and writes to rows. A change that touches one also gets `/code-review ultra` and a fresh run of the pre-launch gate before deploy. A migration also waits for Abdul's OK on its direction, because a deploy carrying one cannot be rolled back. Screenshot checks against the prototype are left to the alignment ticket, which can add them with a reason.

The spec keeps lane steps apart from the toolbox. Lane steps run on every change. The toolbox is the set of skills any session in either lane picks up when it needs one. Take "CSV export on the orders page": the five steps run as always, a timeout on large orders sends the agent to diagnosing-bugs, and a doubt about cancelled orders sends it to grilling with Abdul for two minutes. The next change, renaming a button, uses no tool at all. One toolbox serves both lanes, so the fast lane uses all of it.

parallel-hunt stays in a smaller form and runs only when Abdul types the command. The finder, the fixer and the adversarial gates stay. Each bug the gates confirm ends as a fix with a test, or as a change note for Abdul. The promotion agent, the register's issue files and the queue go. `/code-review ultra` does not replace the hunt, because it reviews a diff and cannot search a live product. Open change notes from a hunt appear on the brainstorm session's page under their product. The routine reads only the ideas repo, so the hunt adds one line per open note there, as the MVP list already works.

Skills, from the 35 today:

- Toolbox (23): codebase-design, coderules, designrules, diagnosing-bugs, domain-modeling, grill-me, grill-with-docs, grilling, handoff, improve-codebase-architecture, panel-review, parallel-hunt, prototype, research, resolving-merge-conflicts, tdd, teach, to-questionnaire, wait-what, wayfinder, wizard, writing-for-agents and writingrules. The three rules pointers are steering, and "Which steering files each lane loads, and the new CLAUDE.md" decides where they load. writingrules stays private.
- Version 1 record (12): to-prd, to-issues, harden-issues, run-issues, implement (the `/goal` session replaces it), premise-check, daily-brief, questionrules, run-compare, triage, setup-matt-pocock-skills and ask-matt. run-compare's records stay, because the version story needs their numbers. The chain scripts in `lib/` retire with these skills.

Agent files follow their skill. The six run-issues agents, the two harden-issues agents and promotion retire. The five parallel-hunt agents and the two panel-review agents stay.

Hooks keep only what refuses something unsafe or something that cannot be undone, moved into `autoMode.hard_deny` or a deny rule where one can carry it. Six stay: coderules-gate, git-shared-state-guard, machine-wide-kill-guard, headless-chrome-guard (the browser pass runs on every change), machine-preflight (hunts still run long) and pilot-database-guard, which stays private. The other 27 retire: the 17 run-issues guards, the eight version 1 hooks, browser-budget (a preference), fixed-sleep-guard (the Monitor tool does its job) and worktree-base-drift (the desktop app syncs worktrees with the base branch). One rule is new: the hard deny on live keys and secrets in code that "What the fast lane does, from brief to done" asked for.

This also settles the fog item on daily-brief and the decisions queue: both retire. Neither lane stops mid-run to ask, and each session reports at its end.

`CONTEXT.md` now defines change note, lane step, toolbox and risk class.

Changed by "How someone installs it" (2026-10-30): machine-preflight stays private in `~/.claude/` with pilot-database-guard, so four hooks ship. A plugin cannot carry permission rules, so a refusal that ships stays a hook. Moving a refusal into `autoMode.hard_deny` or a deny rule now applies to private refusals only, the live-key rule among them.

Corrected by "How the README tells the version story" (2026-10-30): Orderflow is finished and runs the orders of a real business. It was slow, not half done, and the reason for retiring the chain stands: 728 issue files and 2,528 commits for one product in six weeks. The toolbox keeps its 23 skills, but 18 of them now arrive through Matt Pocock's plugin, as the note in "How someone installs it" records.

Changed by "How the careful lane keeps every slice aligned to the core design" (2026-10-31): screenshot checks are now in the careful lane. The pattern and module checks run in "tests and typecheck" and a screenshot test against the graduation baseline runs in the browser pass, so the five lane steps stay five. A note that changes the core design says so and carries Abdul's approval from the interview.

Changed by "How a feature with several change notes runs without Abdul" (2026-10-31): no lane step uses `/code-review ultra` any more. Its three free runs are a one-time allowance per account, and each review after that costs $5 to $25 in usage credits outside the subscription. A risk-class change gets `/code-review max` with the money, sign-in and secrets rubric instead, and ultra stays in the toolbox for a change Abdul chooses to pay for. The pre-launch gate before deploy is now steps 1 to 7, the ones a code change can break; steps 8 to 10 run at graduation and when a change touches backups, accounts or the database host. For a feature of several notes, lane step 2 becomes one agent per note inside `/build-feature`, with other agents running its checks; a one-note change keeps its `/goal` session.

Changed by "What the verifier checks in the browser" (2026-11-01): a one-note change starts a fresh verifier subagent from the `/build-feature` agent file before it merges, and that verifier runs the hostile walk.

Changed by "What the interview settles before a run" (2026-11-01): a one-note change gets `Merged: <date> <commit>` in its note when it merges. Before a session builds a one-note change, it runs the note's done checks once on today's code, and stops if the note says merged or a done check already passes. The authentication risk class covers who may read or write which data, so rights rows and row policies count.
