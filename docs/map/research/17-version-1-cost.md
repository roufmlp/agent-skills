Status: done
Type: research result for ticket 17, version 1 cost

# What version 1 cost, and where its time went

Measured on 2026-10-30, read-only. I read the records that every run-issues and parallel-hunt finale writes (`.scratch/workflow-audit/runs.jsonl` and `issues.jsonl` in `~/code/orderflow`, `~/code/procurement` and this skills repo), the ledgers, merge briefings, run journals and `steps.jsonl` files beside them, and the git history of each main branch. I read the scripts that write the records (`run_costs.py`, `run_timings.py`, `run_session.py`, `run_measures.py`, `run_records.py` and `run_quality.py` in `~/.claude/skills/run-issues/`) to learn what each field measures. I ran no script that writes records and opened no session transcript. The aggregation scripts live in the research session's scratchpad and will not outlast it, so every figure below names its source.

## The answer

Version 1 spent **69.4 minutes of run time per shipped issue**: 846.9 hours across 84 measured runs for 732 shipped issues, 30 August to 28 October 2026. Orderflow alone, in the map's window of 9 September to 24 October, spent **68.7 minutes**: 652.7 hours across 67 measured runs for 570 shipped issues. The median run is cheaper, 63.0 and 61.7 minutes per issue, because a few long runs pull the mean up. With the bug hunts added, version 1 comes to 76.5 minutes and Orderflow to 75.1.

Run time is a run's wall clock, from its transcript's first line to its last. Inside Orderflow's runs a subagent was working for 76% of it and nobody for 20%. Of the agent hours, implementing took 54.5%, the review gate 21.7%, the verify gate 17.9% and the finale 3.9%, so the two gates together took 40%. The README's sentence "Then I measured where the time went and cut most of it" can stand on that for the time inside the runs. "Cut most of it" is a claim about version 2 and waits for version 2's figure.

The records cover the runs and the hunts, nothing else. In Orderflow's window, 1,334 of the 2,528 commits on main (53%) landed while no run session was open: hunts, hardening, rulings, merges, prototypes and Abdul's own sessions. No record says how long that work took, none holds a wait on a usage limit, and none holds money. The 69 minutes are the cost of the build loop, not of the whole pipeline.

## Why run hours per shipped issue

| Unit | Source | Coverage | Spread across Orderflow's five periods | Readable in version 2 without `run_costs.py` |
|---|---|---|---|---|
| Run hours | `hours` on each run line | 83 of 84 measured runs on the line, one from its merge briefing | 46.8 to 89.9 minutes per issue | Yes: a transcript's first and last timestamp |
| Agent hours | the per-role table in each merge briefing | 74 of 84 runs | not tabulated; parallel spawns count twice | Only with a script over subagent transcripts |
| Weighted tokens | `weighted`, one figure per model | every line | cannot be compared: the main model changed three times | By hand, per session, from `/usage` |
| Money | nowhere in the records | three `/usage` readings from August | $8 to $70 per issue, API-equivalent | By hand, per session, from `/usage` |

Hours win on coverage, on stability and on version 2. Every line a finale wrote has them, back to 30 August; only the eleven lines backfilled after the fact lack them. They moved by a factor of 1.9 across Orderflow's periods while the API-equivalent moved by 8.6, mostly because the model and its cache price changed, not the work. Weighted tokens cannot be totalled across models at all: `run_session.py` refuses that and any dollar figure in its `MIXED_NOTE`, and the main model went from Opus 5 to Opus 5.5 around 23 September, to mostly Sonnet 5.5 from 2 October, and back to Opus 5.5 from 15 October. Version 2 can read hours the same way without the version 1 scripts.

The weakness of hours is that a waiting session costs as much as a working one. Abdul's answers, permission prompts and a usage limit inside a session all count, and a session left open counts in full.

The unit divides by shipped issues, not graded ones. The records' own per-issue figure, `faster.wall_minutes_per_issue`, divides by graded status rows, blocked issues included. On Orderflow's 66 window lines that gives 599.0 hours over 610 rows, 58.9 minutes (the field's median is 53.8), about 10 minutes under the shipped figure. "Cost per shipped feature" means shipped.

| Period | Runs | Shipped | Mean minutes per issue | Median run | Main subagent model | API-equivalent per issue |
|---|---|---|---|---|---|---|
| Orderflow, 12-20 Sep | 13 | 111 | 89.9 | 83.1 | Opus 5 | $70.5 |
| Orderflow, 23 Sep-1 Oct | 18 | 136 | 64.9 | 52.3 | Opus 5.5 | $13.7 |
| Orderflow, 2-14 Oct | 27 | 251 | 60.3 | 57.1 | Sonnet 5.5 (78% of cache reads) | $8.2 |
| Orderflow, 15-22 Oct | 9 | 72 | 72.3 | 67.0 | Opus 5.5 | $12.4 |
| Orderflow, 27-28 Oct | 4 | 27 | 46.8 | 39.1 | Opus 5.5 | $10.1 |
| Procurement, 30 Aug-19 Oct | 11 | 130 | 77.5 | 75.6 | Opus 5 (4 runs priced) | $36.6 |
| Skills repo, 27 Sep | 2 | 5 | 62.3 | 84.1 | Opus 5.5 | $15.7 |

The model column is each period's largest share of cache-read tokens in the role tables. The money column is explained under "Money" below.

## What counts, and the double-counting checks

**Version 1** began before its records. The skills repo's first commit, on 19 July, is a baseline taken after the first run, and procurement's git starts on 4 July. The first run line is dated 30 August. So "all of version 1" here means every run with a recorded wall clock, 30 August to 28 October: 72 Orderflow runs, 11 procurement runs and 2 in this repo. Procurement's July and August runs are mostly missing: its `.scratch` run folder holds 44 merge briefings for 43 runs, 38 of them dated July or August, against 11 runs with hours.

**A shipped issue** is a ledger status row at `done`. I checked each row's committed sha with `git merge-base --is-ancestor <sha> main` (`master` in this repo). 601 of Orderflow's 605 done rows reach main. The other four name no commit, or one that does not resolve, and one of them reads "landed short"; I count all 605 because the ledger does. Five more Orderflow rows at `done` record repairs to tests that were already failing. They are not issues and stay out. All 130 procurement rows and all 5 here reach main.

**Run hours** is the line's `hours`: the wall clock `run_timings.py` reads over the newest main transcript only. `run_costs.py` passes it the last session, because adding two sessions would count the gap between them.

The checks:

- **Repeated batch ids.** None in any of the three `runs.jsonl` files. `run_costs.py` refuses a second line for a batch id already present. The one duplicate from before that rule, a second line for the procurement run `review-375cbf` on 1 September, was deleted by hand on 6 September, as `run_records.py` records.
- **Resumed runs.** One briefing shows two sessions: batch-24d0d1, an Orderflow run resumed in a new session on 22 September after a halt. Its line holds the 13.33-hour resume. The launch session, 21 September 20:10 to 22 September 18:53 UTC, 22.72 hours, appears only in the briefing's earlier printout, so I added it. Every other run's line is at least as long as its git span, first issue commit to last, so no other run shows a lost session that made commits.
- **Runs with no line.** batch-7f5b53, an Orderflow run merged on 17 September with 16 issues shipped, has a 30.91-hour briefing printout and no line; I used the printout. batch-d914e4, an Orderflow run halted at the finale on 18 October with 8 shipped, has no reading at all. Its 8 issues count as shipped but sit outside the per-issue figure. Its git span is 8.86 hours.
- **Borrowed lines.** Procurement's first 12 lines are marked `borrowed`. Until skills commit aa94b3b of 6 September, the change that made the cost scripts take a batch id, `run_costs.py` copied their issue counts and tokens from whichever run came last. `run_records.py` says their `hours` and `idle` were always their own. Eleven are backfilled with no hours. The twelfth, dated 30 August, holds 15.02 hours and no batch id. Its ledger in procurement's `.scratch` run folder, `archive-run-414a-483-286335.md`, shows 9 issues done with all 9 commits on main, so I counted it.
- **Trial lines.** Four Orderflow lines and one here carry `trial: void`. That voids the model comparison, not the work (`VOID_MEANS` in `run_quality.py`), so they count.
- **Hunts.** Hunts have their own lines (`kind: hunt`) and no issue lines. I keep them out of the run figure and report them beside it.
- **The line's `issues` field.** It is typed by hand or counted from spawn labels, and it is not a shipped count. It differs from the ledger in 21 of 70 Orderflow lines, which total 544 issues (three blank) against 581 shipped. I used the ledgers.
- **Overlapping runs.** Runs sometimes ran side by side, as the Orderflow runs batch-e35a25 and batch-04dff9 did on 27 and 28 September. Run hours are machine hours, not calendar hours.

## Version 1 in figures

Orderflow:

| | Map window, 9 Sep to 24 Oct | All records, to 28 Oct |
|---|---|---|
| Runs found, measured | 68, 67 | 72, 71 |
| Shipped in all runs, in measured runs | 578, 570 | 605, 597 |
| Run hours | 652.67: 599.04 on 66 lines, 22.72 for batch-24d0d1's launch, 30.91 for batch-7f5b53 | 673.73: adds 21.06 for four runs on 27 and 28 October |
| Mean per shipped issue | 652.67 / 570 = 1.145 h = **68.7 min** | 673.73 / 597 = **67.7 min** |
| Median run (25th, 75th percentile) | 61.7 min (45.6, 83.1) | 59.7 min (43.8, 82.0) |
| Hunts | 4, 60.39 h | 4, 60.39 h |
| Runs and hunts per shipped issue | 713.06 / 570 = **75.1 min** | 73.8 min |

The Orderflow figure uses the map's window. The four runs dated 27 and 28 October (27 shipped) fall after it and lower the figure by one minute.

All of version 1:

| Repo | Runs measured | Shipped | Run hours | Mean minutes per issue | Median run | With hunts |
|---|---|---|---|---|---|---|
| Orderflow, 12 Sep to 28 Oct | 71 | 597 | 673.73 | 67.7 | 59.7 | 73.8 |
| Procurement, 30 Aug to 19 Oct | 11 | 130 | 167.99 | 77.5 | 75.6 | 89.8 (one hunt, 26.59 h) |
| Skills repo, 27 Sep | 2 | 5 | 5.19 | 62.3 | 84.1 | 62.3 |
| All | 84 | 732 | 846.91 | **69.4** | **63.0** | **76.5** |

846.91 / 732 = 1.157 h = 69.4 minutes; with the five hunts' 86.98 hours, 933.89 / 732 = 76.5 minutes. The 25th and 75th percentile runs sit at 46.1 and 83.2 minutes. batch-d914e4 brings the shipped count to 740, without hours.

A git cross-check gives less: from first to last issue commit, Orderflow's 68 window runs span 530.2 hours, 55.0 minutes per shipped issue. A session starts before its first commit and ends after its last, so this is a floor.

## Against the map

The map says Orderflow "took 728 issue files and 2,528 commits between 9 September and 24 October". Both counts hold: 728 issue files existed at the last commit on main on 24 October, and main holds 2,528 commits in the window. Neither counts features.

- Of the 728 issue files, 622 were done: 578 through runs, 25 through the direct road and 19 another way. 73 were parked, 29 closed and 4 waiting for hardening. Today there are 753, of which 650 are done.
- Of the 2,528 commits, 746 sit on the runs' own branches, fork point to last issue commit. 1,334 (53%) landed while no run session was open.
- The window is 1,104 clock hours. The runs used 652.7 hours in it, which is 27 days of non-stop running, but because they overlapped, a run session was open in only 550 of the 1,104 hours (50%).

## Where the time went inside the runs

Wall clock, Orderflow's window:

| | Hours | Share |
|---|---|---|
| A subagent running | 495.2 | 75.9% |
| Nobody running | 133.6 | 20.5% |
| Not split (batch-f562a0) | 24.0 | 3.7% |
| Total | 652.7 | 100% |

The split is `hours` times `idle` on 65 lines, plus the briefing printouts for batch-7f5b53 and for batch-24d0d1's launch session (12.59 hours busy, 10.12 idle). batch-f562a0, an Orderflow run of 22 October, reads 99.8% idle: in desktop app 2.1.304 every spawn ran in the background, where the timing script cannot see it, as its line's note says.

"Nobody running" covers the main thread's own turns, Abdul's answers, permission prompts and any usage-limit wait inside a session. Before 25 September it also held gate time. On 4 September skills commit f03e824 moved the verify gate into the background so the two gates overlap, and until 24 September, when skills commit 26be168 taught the run clock to read a backgrounded step to the end of its own transcript, a backgrounded spawn read as instant. The fix's docstring shows one Orderflow run, batch-46e4de, reading 27% idle before it and 9% after. Orderflow runs before 25 September read 28.9% idle (15 runs); runs from 25 September read 16.2% (51 runs), or 9.4 minutes per shipped issue. Trust the later figure.

Agent hours by stage, Orderflow's window, 64 runs with a role table, 550 shipped:

| Stage | Roles in the table | Hours | Share | Minutes per shipped issue |
|---|---|---|---|---|
| Implementing | implementer, escalated implementer | 305.3 | 54.5% | 33.3 |
| Review gate | review 66.7, critical review 55.1 | 121.8 | 21.7% | 13.3 |
| Verify gate | verify | 100.3 | 17.9% | 10.9 |
| Finale | finale, promotion | 21.8 | 3.9% | 2.4 |
| Other helpers | general-purpose, Explore | 7.7 | 1.4% | 0.8 |
| Hardening inside runs | attacker, seam | 3.3 | 0.6% | 0.4 |
| Total | | 560.1 | 100% | 61.1 |

The role tables are `render_roles` in `run_session.py`, printed into each merge briefing. Each spawn's hours run from its own transcript's first line to its last, so backgrounded gates count properly and two gates running at once count twice: the same 64 runs had 613.5 hours of wall clock. Rows for the model `<synthetic>` repeat other rows' hours and are left out. Four window runs have no role table: batch-26c495 and batch-2957c3 carry only `longest_steps`, batch-7f5b53 has no line and batch-d914e4 has nothing.

Across all of version 1 (74 runs with a role table, 617 shipped, 632.5 agent hours) the split barely moves: implementing 52.5%, review 21.9%, verify 18.6%, finale 4.3%, other helpers 2.1%, hardening 0.5%.

A spawn's hours include its own waiting. Procurement's run batch-200d42 lost 5.7 hours to a permission prompt in September, 230 minutes of it inside a verify gate that the table counts as gate time (`~/code/procurement/.scratch/workflow-audit/where-batch-200d42-idled-2026-09-12.md`).

The issue lines (`issues.jsonl`) of the 554 done issues in recorded window runs show what fed the gates:

- 180 issues (32%) went through the critical review gate, the money, auth and secrets variant, which is why its hours come close to the ordinary gate's.
- 138 needed a second attempt (`attempts` above 1), with 367 correction rounds and 138 strikes between them. None escalated to a third implementer.
- An issue's loop, first spawn to last (`span_minutes`), took a median of 34.8 minutes and a mean of 46.3, over the 458 issues with a span.
- Spawns labelled correction, retry, strike-2 or finish took at least 38.8 hours, from the "agent time by first word" printouts in the briefings. That printout lists the top ten words only and misses backgrounded steps (it reads verify at 46.2 hours against 100.3 in the role tables), so 38.8 is a floor.

Whole test suites are counted, not timed. The line's `suites` field counts 1,357 whole-suite runs across 61 window runs: 234 by the runner and 1,123 inside subagents. Only the runner's are timed: `steps.jsonl` stamps 86 suite runs in the window, 8.96 hours, median 5.7 minutes each. A suite inside an implementer or a gate is part of that spawn's hours and cannot be split out. An earlier audit that read the transcripts of two runs, batch-e35a25 and batch-04dff9 (`~/code/orderflow/.scratch/workflow-audit/perf-audit-2026-09-28/audit-pair1.md`), put whole suites at 98 to 104 minutes per run.

Orderflow's four hunts took 60.39 hours: 15.0 on 18 October, 10.76 on 19 October, 27.46 on 21 October and 7.17 on 24 October. Their registers hold 228 rows: 177 verified, 40 deferred and 11 retracted. Only hunt-62b745, the hunt of 19 October, has a role table, in `~/code/orderflow/.scratch/orderflow-v1/round-journal.md`: finder 6.87 hours, fixer 9.0, claim gate 1.17 and fix gates 7.46, so 24.5 agent hours in a 10.76-hour hunt. For the other three hunts and for procurement's hunt, the stages exist only in `longest_steps`, the single longest step per kind, and I give no hours for them.

## Where the time went outside the runs

Apart from the hunts' lines, git is the only record. I placed each Orderflow run session in time from the "wall clock ... UTC" line of its briefing printouts (71 runs, plus hunt-62b745 from the round journal), added batch-d914e4's git span, and checked every commit on main in the window against those sessions. The other three hunts left no printout, so their commits count as outside.

- 1,334 of the 2,528 commits (53%) landed while no run session was open.
- 331 of the 732 clock hours that hold a commit (45%) had no run session open.

A rough keyword sort of the 1,334 by subject line: 328 fixes, features, tests and chores; 266 hunt, register and bug rows; 243 rulings, decisions, walks and briefs; 208 merges; 101 naming a run (finale records and merges after the session closed); 70 PRDs, issue files and the map; 65 hardening; 48 prototypes and design; 3 docs; 2 direct road.

A commit marks when work landed, not how long it took, so none of this converts to hours.

## Money

The records hold none. `run_session.py` refuses a dollar figure, and its `MIXED_NOTE` sends the reader to "read the `/usage` screen by hand". Three sources give part of the answer.

**Three `/usage` readings from procurement, 16 to 20 August** (`~/code/procurement/.scratch/workflow-audit/usage-baseline.md`), from before the records began. Each covers a whole session, main thread included, at list price, on Opus 5: $426.75 for 9 issues, $642.69 for 13 and $513.67 for 9, which is $47.42, $49.44 and $57.07 per issue. The weekly all-models limit moved 10, 13 and 10 percentage points, about one point per issue.

**The role tables priced at list**, subagents only. I priced each model's input, cache-write, cache-read and output tokens at the rates on platform.claude.com/docs/en/about-claude/pricing, fetched 2026-10-30, with cache writes at the 5-minute rate for the low figure and the 1-hour rate for the high one. Orderflow's window, 64 runs: $11,228 to $12,465, or $20.4 to $22.7 per shipped issue. All of version 1, 74 runs: $12,861 to $14,285. By period the cost fell from $70.5 per issue on Opus 5 to between $8 and $14 on Opus 5.5 and Sonnet 5.5. Most of the fall is cache reads: the Opus 5 runs read 120 million cached tokens per issue at $0.50 per million, the first Opus 5.5 runs about 49 million at $0.20.

Rates used, dollars per million tokens, in the order input, 5-minute cache write, 1-hour cache write, cache read, output: Opus 5.5 4, 5, 8, 0.20, 20. Opus 5 5, 6.25, 10, 0.50, 25. Sonnet 5.5 2, 2.50, 4, 0.10, 10. Sonnet 5 2, 2.50, 4, 0.20, 10.

**The main thread** is not in the role tables. The line's `orchestrator` field gives its share within one model only: a median 20% of the Opus weighted tokens in the window. A share within one model cannot lift a total across models, so I add nothing for it, and the role-table figure is a floor.

The token counts have a hole. Output tokens per issue read 78,000 in Orderflow's Opus 5 period and 113,000 on 27 and 28 October, but 12,000, 7,000 and 3,000 in the three periods between, 23 September to 22 October. Implementers that write code and tests, and gates that write verdicts, cannot produce 3,000 tokens of output an issue between them, so the counter lost them. `run_session.py` keeps the first transcript row for each message id, to skip retried turns. If the Claude Code versions of those weeks wrote several rows per message with a running output count, the first row holds only part of it. I could not check this without opening transcripts. Output is a small part of the price, so the hole lowers the API-equivalent by about $2 per issue at most and the weighted tokens of those weeks by up to a tenth.

On Abdul's subscription none of these dollars was a bill: the Claude Code docs say the `/usage` session cost "isn't relevant for billing purposes" for Pro, Max and Ultra subscribers (code.claude.com/docs/en/costs). The cost that bit was the weekly limit. It ran at about one percentage point per issue in August, and the weekly all-models bar read 100% on 15 August (`~/code/procurement/.scratch/workflow-audit/usage-measured.md`).

## What the records cannot give

- **Waits on usage limits.** No field holds them. Inside a session they fall into "nobody running" with everything else, and between sessions nothing records them. Two appear in run journals and briefings: batch-24d0d1 sat for 181 minutes on a session limit on 22 September, and batch-6f777a, an Orderflow run of 11 October, idled about 147 minutes on the weekly limit. Both sat inside a session, so both are in "nobody running".
- **Earlier sessions of a resumed run, and the gaps between sessions.** `hours` reads the newest session. I found one lost session and added it back. A resume that left no briefing printout would be missing without trace.
- **Hours outside the runs.** Git gives commits and clock hours with a commit, not how long a hardening pass, a walk or a direct-road fix took.
- **Suite time inside spawns, and a stage split per issue.** The issue lines carry the loop span and summed agent minutes, not minutes per role.
- **The stages of three Orderflow hunts and the procurement hunt.** Only `longest_steps`.
- **Money**, and the output tokens of 23 September to 22 October.
- **Procurement's unrecorded runs.** 32 of the 43 runs with a merge briefing have no line, most of them from July and August. The three August `/usage` readings are the only measurement of that period.
- **batch-d914e4**, the Orderflow run halted at its finale on 18 October: 8 shipped, no reading.

A transcript reading would fill most of this: the usage-limit messages and the gaps around them, every session of a resumed run, each suite's start and end inside a spawn, the full output tokens from the last row per message, the first and last line of every session outside the runs, and procurement's July and August runs. It should be a script, not a model reading. The store holds 8,470 transcript files, 10 GB: Orderflow 4,647 files and 6.9 GB, procurement 3,483 and 2.8 GB. A model reading 10 GB would cost billions of tokens. A streaming Python pass reads it in minutes, and writing and checking the script should take a few hours of one session. The files reach back far enough: by creation date, procurement's main transcripts run from July (41 in July, 278 in August, 145 in September, 12 in October) and Orderflow's from September (193 in September, 325 in October).

Retention is the risk. Claude Code removes session files older than `cleanupPeriodDays` at startup, 30 days by default (code.claude.com/docs/en/costs). I found no override in `~/.claude/settings.json` or the project settings. Yet files last modified in August are still on disk, and most files carry an October modification date though created earlier, so I cannot tell when the rule will bite. If the transcript pass is wanted, run it soon or raise `cleanupPeriodDays` first.

## How to measure version 2 the same way

Version 2 will not have `run_costs.py`, so measure with the instrument underneath it: a session's wall clock, from its transcript.

**Fix the unit first.** Version 1's unit is one issue file: one slice with its own acceptance criteria, whose loop took a median of 35 minutes. "How a regular audit keeps the workflow small" has to say what a version 2 feature is, a change-note item or a brief line, and how its size compares, or the two figures measure different things.

**Count shipped features** as version 1 did. A feature counts when its commit is on main:

```
for s in <sha> <sha>; do git -C ~/code/<product> merge-base --is-ancestor "$s" main && echo "$s shipped"; done
```

**Sum the build sessions' wall clock.** Claude Code writes each session to `~/.claude/projects/<folder>/<session-id>.jsonl`, where the folder is the session's working directory with each `/` turned into `-`; worktree sessions get longer folder names. List a product's sessions, newest first:

```
ls -lt ~/.claude/projects/*-code-<product>*/*.jsonl
```

Then read the wall clock of the build sessions, each and in total:

```
python3 - ~/.claude/projects/<folder>/<session-1>.jsonl ~/.claude/projects/<folder>/<session-2>.jsonl <<'EOF'
import json, sys, datetime as d
total = 0
for f in sys.argv[1:]:
    t = sorted(j["timestamp"] for j in (json.loads(l) for l in open(f) if l.strip()) if "timestamp" in j)
    a, b = (d.datetime.fromisoformat(x.replace("Z", "+00:00")) for x in (t[0], t[-1]))
    h = (b - a).total_seconds() / 3600; total += h
    print(f"{h:6.2f} h  {t[0]} to {t[-1]}  {f}")
print(f"{total:6.2f} h  total")
EOF
```

This is what `run_timings.py` measured for a run: first timestamp to last in the main transcript. Count build sessions only, the counterpart of runs. Bug-fixing sessions after a feature ships are the counterpart of hunts; report them as the second figure, as version 1's 76.5 minutes does.

**Read the cost by hand at the end of each session**, before `/clear` resets it. The `/usage` Session block gives "Total duration (wall)", a check on the script, and "Total cost" at list price, comparable with the August readings. Note the weekly all-models bar before and after a product's build.

**Cross-check with git.** The span from a branch's first commit to its last, for a branch forked at `<fork>`:

```
git -C ~/code/<product> log --first-parent --format=%ct <fork>..<head> | sort -n | awk 'NR==1{a=$1} {b=$1} END{printf "%.2f h over %d commits\n",(b-a)/3600,NR}'
```

Version 1's matching git figure is 55.0 minutes per shipped issue for Orderflow's window.

**Measure within 30 days** of each session, or raise `cleanupPeriodDays`, because the transcripts are the only record.

Compare the result with version 1's 69.4 minutes per shipped issue (Orderflow's window 68.7, median run 62), or 76.5 with hunts.
