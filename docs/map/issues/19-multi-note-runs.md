Status: resolved
Assignee: Abdul (wayfinder session 2026-10-31)
Type: grilling
Blocked by: 08, 13

# How a feature with several change notes runs without Abdul

## Question

Abdul asked on 2026-10-31 whether a feature cut into several change notes runs one note at a time on his command, or unattended in order, the way `/run-issues` runs today. He wants the second: he starts the feature once and the notes run without him. "What the careful lane keeps" gives each note one auto-mode session and retires `/run-issues`, but no ticket says what starts the next note's session. "What recent Claude Code features and Anthropic posts can replace" suggested one saved workflow that resumes after a stop and waits for the usage limit to reset. Decide what runs the notes in order, what happens when one note fails its checks, and where Abdul sees the result. "How the careful lane keeps every slice aligned to the core design" decides what keeps those notes in line with each other; this ticket decides how they run.

His second question belongs here too. For request-kinds he answered about 100 decisions by his own count, and the parts that raised most of them, hardening and the queue of defaults, retire in version 2. Decide which questions he still gets for a feature: what the interview asks up front when Claude writes the notes, what an unattended session does with a fork it meets mid-run (take a default and list it in its end report, or stop), and which calls must wait for him. "What the careful lane keeps" names one, a migration's direction. Version 1 also held money and sign-in rules, a `wontfix` close, and anything that ships data or commits a public contract.

Changed by "How a regular audit keeps the workflow small" (2026-10-31): Abdul wants two things beyond running notes in order. He wants the notes of one feature, or two separate changes, to run in parallel, aiming at the most work in the least time at low cost. And he wants runs of two or three days without him, so he needs to know what stops one. The audit now counts every interruption (30 minutes with nothing writing in an unfinished session) with its cause, and the most sessions running at once. This ticket decides how parallel runs work and what keeps a long run from waiting on him. The audit also counts the questions he gets per note, which answers his second question with numbers once version 2 has run.

Changed by "How the careful lane keeps every slice aligned to the core design" (2026-10-31): when Claude cuts a feature into notes and two need the same new pattern, the pattern goes to one note and the others wait for it. This ticket decides how a note waits. A session that meets an unapproved new pattern mid-run stops that part and lists it in its end report, which answers one of the forks above. Full suites from several notes running at once on one laptop are for "How the careful lane keeps the test suite fast and trusted".

Changed by "Which steering files each lane loads, and the new CLAUDE.md" (2026-10-31): a fork that an unattended session meets now has a home. When its default is hard to undo or the choice is Abdul's, the session writes it under "Decide" in `~/.claude/pending.md`, with the default it took, the case for and against each choice and what reversing it costs; every other default goes in its end report alone. This ticket still decides which forks stop a run and which take a default.

## Answer

A feature runs as one saved workflow, `/build-feature <name>`, which the plugin ships. Abdul types it once and the notes run without him, in order and in parallel where they can. The run keeps its state in git, so a lost session loses at most the attempts that were running. Abdul answers every question that could stop a run in the interview, before it starts.

**Feature.** A change too big for one session, which Claude cuts into change notes that run as one group. A change of one note is not a feature, and it still runs as one session with `/goal`, as "What the careful lane keeps" set out.

**Before the run.** Claude writes all the notes of a feature in one interview, after reading the code each note touches. Abdul approves one page: a line per note, the order, which notes wait for which, and four kinds of question. Those are each core-design change, each migration's direction, each money or sign-in rule the feature changes, and each change that sends data out of the product or commits a public contract such as an API, a webhook or an email format. He does not read the notes. Each note carries a "Waits for: 02, 04" line, and a note that adds a shared pattern goes before the notes that use it. Every done check must be a command. Before the run starts, a verifier runs each check once on today's code, and a check that already passes is refused, because it proves nothing.

**Who does what.** The workflow script is the orchestrator. It is plain JavaScript, it judges nothing, and the workflows docs say it cannot run commands, so agents run every check. Each note gets fresh agents, each in its own worktree:

| Role | Job | Default model and effort |
|---|---|---|
| Implementer | Builds the note | Sonnet, high |
| Verifier | Runs the done checks, tests, typecheck and the browser pass; changes no code | Sonnet, high |
| Reviewer | The `/code-review` lane step, against the note and the core design | Opus, high |
| Note checker | Only after strike two, below | Opus, high |
| Merger | Merges each passed note into the feature branch, and the feature into local main | Sonnet, medium |
| Final verifier | Full suite, typecheck, every baseline screenshot and the main-flow browser pass on the merged branch | Sonnet, high |
| Final reviewer | `/code-review` on the whole feature diff against the brief, the core design and all the notes; `max` effort and the money, sign-in and secrets rubric for a risk-class feature | Opus, xhigh |

The session Abdul typed the command in starts the run, starts it again after a stop, and sends the phone notification. The implementer never grades its own work. Lane step 2 for a feature therefore reads "one agent per note, whose checks other agents run" rather than "one session with `/goal`".

**Models and effort.** Each role is one agent file in the plugin with `model` and `effort` in its frontmatter, so Abdul changes a role in one line of his working copy. One run can override a role for a trial, for example `/build-feature request-kinds implementer=opus:medium`, through the workflow's `args`. Every report records model, effort, tokens, cost and strikes per role, and the audit compares them month by month. After three audits Abdul picks the permanent defaults from the numbers; Sonnet high against Opus medium for the implementer is the first comparison. `CLAUDE_CODE_EFFORT_LEVEL` must stay unset, because it overrides every effort setting.

**Parallel.** At most three notes of one feature run at once, and at most two features. Version 1 shows why the numbers start low: one suite took 6,120 seconds beside a second run against 591 alone, and two of six parallel pairs hit merge conflicts. "How the careful lane keeps the test suite fast and trusted" decides how full suites share the laptop and may raise both numbers.

**Strikes.** A reject from the verifier or the reviewer is a strike. After the second, a fresh note checker reads the note, both failure reports and the code. If a check in the note is wrong and the right check stays inside what Abdul approved, it corrects the note, the change goes in the end report and a third attempt starts, which is not a strike. If the note is sound, a fresh implementer makes the third attempt with both reports and none of the failed reasoning. If the fix would change something Abdul approved, the note stops and the question goes under "Decide". A note gets one correction. After a third failure it fails, its branch stays, the notes that wait for it do not start, and the rest carry on. A merge conflict the merger cannot resolve counts as a strike, and the note tries again from the current feature branch. This is a default, not a ruling. Version 1's records back the shape: of 637 Orderflow issues, 447 passed first time, 125 on the second attempt, 22 on the third and 4 after that, and the escalated implementer ran no times, so every third attempt came from the criteria check at strike two.

**Forks mid-run.** A session stops a note only for the four kinds of question above, or for a new pattern Abdul has not approved, as "How the careful lane keeps every slice aligned to the core design" ruled. Every other fork takes a default. A default that is hard to undo goes under "Decide" in `~/.claude/pending.md`; the rest go in the end report. No version 1 run left alone ever waited for an answer either: its briefings hold 494 "Ruled" and 351 "Decide" items.

**The final check.** After the last note merges, the final verifier and final reviewer run on the whole feature, because each note's reviewer sees only its own diff and the problems between notes need a reader of the whole. If either finds a problem, a fresh implementer fixes the findings in one round and both run again. If the problem stays, the feature does not merge to local main and the report lists the findings.

**Risk classes.** No lane step uses `/code-review ultra`. Its three free runs are a one-time allowance per account, and each review after that costs $5 to $25 in usage credits outside the subscription, so a risk-class feature gets the final reviewer at `max` instead, inside the plan. Ultra stays in the toolbox for a change Abdul chooses to pay for. Before the push, an agent runs steps 1 to 7 of the pre-launch gate on the feature branch, the steps a code change can break. Steps 8 to 10 (backups with a restore, MFA on platform accounts, the Supabase production checklist) run at graduation, and again only when a feature changes backups, accounts or the database host.

**State and recovery.** A note that passes merges into the feature branch at once, and the merger then updates `changes/<feature>/report.md` on that branch with each note's state: merged, failed, stopped or not started. That report is the ledger. Typing `/build-feature <name>` again, from any session on any day, reads the report and the branch, skips the merged notes and carries on. A worktree with changes stays on disk, but a new run does not reuse it. This matters because the built-in resume works only in the same session and re-runs every agent that started after a failed one.

**Long runs.** Abdul wants runs of two or three days. Four things stop one, and each has an answer:

1. The usage limit. A workflow waits for a reset twice at most, and only in an interactive session on a claude.ai subscription. At the third limit the agent fails. When a run stops early on a limit or an outage, the starting session waits and starts it again, and a session's own wait has no such cap. It gives up after three days, or after three starts in a row with no newly merged note.
2. An outage. The docs say an agent whose output stops restarts up to five times, and one that hits an API error it cannot recover from returns no result. A note with no result is not a strike: the script retries it after the other notes, and if it fails again the run stops as "stopped: API errors".
3. Sleep. The desktop's keep-awake setting stops idle sleep but not a closed lid, so the run turns it on and Abdul keeps the laptop open on power. That step is his because it is physical.
4. Nothing moving. A watchdog checks every 30 minutes and notifies Abdul with the last error when a running feature has written nothing in that time, the same rule the audit uses for an interruption. Version 1 lost 730 minutes once to an expired sign-in that killed a gate nobody saw. Auto mode pauses after three blocks in a row or 20 in all, so a blocked action stops only that note, and one session adds the tools build agents need to the allow rules before the first long run.

**The result.** Abdul gets the one-page report at `changes/<feature>/report.md` (notes merged, failed and stopped, defaults taken, time and tokens), a one-line phone notification such as "request-kinds: 9 of 10 notes merged, 1 failed, 2 to decide", and the "Decide" entries the session-start hook already counts. The feature merges to local main only when every note and the final check pass. The push stays his.

**Budget.** The `build-feature` workflow and its seven agent files count against the plugin budget from "How a regular audit keeps the workflow small", which now counts workflows beside skills, agents and hooks. This is a default.

The facts behind this answer: the [Claude Code workflows docs](https://code.claude.com/docs/en/workflows), the [subagent docs](https://code.claude.com/docs/en/sub-agents), the [ultrareview docs](https://code.claude.com/docs/en/ultrareview), and Orderflow's version 1 records under `~/code/orderflow/.scratch/` (`workflow-audit/issues.jsonl`, the run folders' `merge-briefing.md` and `run.md`).

`CONTEXT.md` now defines feature and done check. It adds to change note that the note is written for the build agent after reading the code, and renames the product state "Retired" to "Stopped", because skills and hooks also retire.

Changed by "What the verifier checks in the browser" (2026-11-01): each note carries a "Screens:" line, and the check before the run refuses a note that names a screen without an end-to-end done check. The verifier also runs a hostile walk of the note's new actions, and a reject there is a strike. The feature report gains a screens section with new screens, and changed screens before and after.

Changed by "What the interview settles before a run" (2026-11-01): `/build-feature` is now a skill that runs the interview when the feature has no approved plan and starts the saved workflow, renamed `build-feature-run`, when it has one. The interview makes the feature branch in its own worktree, not the run, and commits the notes, their done-check tests and `changes/<feature>/plan.md` there. The workflow refuses a plan with no `Approved:` line or a note changed after it. The pre-run check runs inside the interview, before Abdul sees the page, and again at each later start on the notes not yet started; a note whose done check now passes stops under "Decide". The skill refuses a feature whose report on local main says merged. The page's "money or sign-in rules" question is now "money or access rules".

Changed by "What a run does when notes collide or fail" (2026-11-01): after a third failure, the next `/build-feature` opens a short interview, not the run. Abdul changes or cuts each failed note, and may cut merged notes, which the merger reverts; a changed note gets three new strikes. Local main merges into the feature branch before the final check, and the merge into main is fast-forward only. The merger sets each migration's number at the merge, and a check refuses two with the same number.

Changed by "Where the note check lives, and baselines for changed screens" (2026-11-01): a note's verifier compares only the screens its note does not name and walks the ones it names. The final verifier retakes the baselines of every named screen once, and the merger commits them. Each note runs on a branch `feature/<name>/<nn>`, which is how the note check finds the note.
