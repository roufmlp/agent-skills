Status: done
Type: research result for ticket 20, Orderflow's test suite

# How long Orderflow's test suite takes, and where it flakes

Measured on 2026-10-31, read-only. Sources: `~/code/orderflow` git history; the suite wrapper's records, logs and flake ledger (`~/.claude/skills/run-issues/run_suite.py`); `runs.jsonl` and `steps.jsonl` from the version 1 records; and 43,583 Bash calls that mention a test command, streamed from all 4,716 Orderflow transcripts under `~/.claude/projects/` (9 September to 31 October, not a sample). The scripts will not outlast the session, so each figure names its source. I ran no test, because every file runs against a worker database; per-kind times come from a full-suite log.

## The answer

- **The gap is growth.** The 197.33 s in `vitest.config.ts` (516 files, 29 September) was true that day. The latest run, batch-d69d80 on 30 and 31 October, read 402 to 590 s, median 488 s, on 1,518 files. The harness suite it owes adds a median 51 s. That is 9.0 minutes a run, so "about ten minutes" holds.
- **Growth:** the weekly median went from 202 s (week of 28 September, about 600 files) to 410 s (26 October, about 1,470 files). Files grew 2.5 times; seconds per file fell from 0.38 to 0.29.
- **Runs per issue:** 2.8 whole suites in the map's window; 2.2 in batch-d69d80 (19.5 machine minutes per issue).
- **Flakes:** 261 failures that passed on a rerun of the same tree since 3 October, in 57 files; five files hold 54%. At most one whole-suite run in four hit one; in batch-d69d80, 2 of 24.
- **Kinds:** 80% of file-seconds are app tests, 16% build-checks; the harness suite (36 files) and 92 end-to-end specs run apart.
- **`vitest related`:** a one-file change reaches a median 12% of files; a typical issue reaches far more.

## The gap

| | `vitest.config.ts` comment | batch-d69d80 |
|---|---|---|
| Time | 197.33 s | 401.9 to 589.9 s, median 488 s, 24 runs |
| Size | 516 files, 10,443 tests | 1,518 files, 22,567 tests |
| Conditions | quiet machine, 8 workers, no coverage | 8 workers, coverage on, machine lock free |

Left: the comment above `fileParallelism` in `~/code/orderflow/vitest.config.ts` (commit c7f3e3df8). Right: `~/code/orderflow/.git/worktrees/run-issues-01-24-d69d80/run-suite/records.jsonl` (22 `issue` and 2 `correction` records) and `logs/20261031T123901.204723Z-issue-6a72470fab67.log` (439.68 s). Coverage is not the cause: wrapper readings (coverage on) and direct `npm test` readings (off) match, 328 against 304 s (week of 12 October), 392 against 352 (19 October), 405 against 424 (26 October). The harness suite (36 files, 325 tests, 48.7 s) follows any diff touching a migration or harness path; together a median 539 s, longest 650 s.

## Growth, September to October

Whole-suite readings from vitest's own `Duration` line (files within 90% of that week's 90th percentile; 526 readings). Tree files: `git ls-tree` on main each Sunday, `*.test.ts[x]` outside `e2e/` (about 36 harness files are counted that the readings omit from 29 September).

| Week | Readings | Median s | 25th-75th | Median files | Tree files |
|---|---|---|---|---|---|
| 14 Sep | 80 | 166 | 156-177 | 405 | 410 |
| 21 Sep | 26 | 275 | 249-419 | 517 | 520 |
| 28 Sep | 108 | 202 | 193-210 | 597 | 729 |
| 5 Oct | 86 | 267 | 249-289 | 849 | 976 |
| 12 Oct | 129 | 327 | 303-340 | 1,021 | 1,260 |
| 19 Oct | 34 | 383 | 341-447 | 1,379 | 1,470 |
| 26 Oct | 63 | 410 | 402-427 | 1,466 | 1,503 |

Two runs shared the machine in the week of 21 September. The runner's own stamps (`steps.jsonl`, 97 suite stamps) agree: median 165 s (14 September), 255 (28 September), 438 (12 October), 597 (26 October), harness suite included. Earlier: 116 s on 361 files (17 September, commit ac230e75f).

## Whole suites per issue

`~/code/orderflow/.scratch/workflow-audit/runs.jsonl`, field `suites`: from 9 September to 24 October, 58 runs shipped 455 issues and ran 1,288 whole suites, **2.8 per issue** (231 by the runner, 1,057 inside subagents). By week from 14 September: 6.6, 4.0, 2.2, 1.7, 2.4, 5.8, 10.8; the last two weeks hold 7 runs.

Batch-d69d80 is the only store still on disk: 24 whole-suite records for 11 committed issues, **2.2 per issue**. Ten were red, each followed by a changed tree; 12 were clean green, 2 green after the flake recheck. Machine time: 196 minutes of suite and 18.5 of harness suite, **19.5 minutes per issue**. The 526 full readings add to at least 42.1 agent hours of waiting.

## Flakes

The ledger is `~/code/orderflow/.git/run-suite-flakes.jsonl`. `run_suite.py` writes a row when a failing file passes alone on the same tree (a rerun of at most 5 files), so every row is a failure that passed with no code change. It starts on 3 October. Before the recheck a flaky red cost a whole-suite rerun: nine cost 34.5 minutes (`run_suite.py` docstring).

- **Size:** 261 rows, 211 red runs, 192 trees, 57 files. 79 red runs were whole suites, 132 scoped. Rows by week from 28 September: 6, 118, 65, 36, 36.
- **Rate:** the transcripts hold 274 wrapper whole-suite readings since 6 October, 111 red (40%), median 1 failing file. 79 flaky whole-suite runs against 284 readings since 5 October is at most 28%. In batch-d69d80: 2 of 24, `tests/storage/object-usage.test.ts` and `tests/regressions/hunt-06eff0-16.test.ts`. Its ten reds were real.
- **Cause:** issue 505, the default test limit (commit 818ca7ea1), found 69 of 112 rows were `Test timed out in 5000ms`, 66 in one file. Of the 19 rows with a log left, 10 are assertion failures, 5 timeouts, 4 other.

| File | All rows | After 11 Oct |
|---|---|---|
| `tests/push/no-timer-calls-the-server.test.ts` | 66 | 0 |
| `tests/jobs/raise-form.test.tsx` | 29 | 23 |
| `tests/jobs/reference-upload-412.test.tsx` | 20 | 11 |
| `tests/bills/bill-form-screen.test.tsx` | 13 | 3 |
| `tests/build-checks/launch-checks.test.ts` | 12 | 12 |
| `tests/harness/kept-databases.test.ts` | 11 | 11 |
| `tests/jobs/jobs-tab-screen.test.tsx` | 9 | 5 |
| `tests/storage/object-usage.test.ts` | 8 | 7 |

After 11 October there are 137 rows on 41 files; the five largest hold 47%.

## Tests by kind

From the per-file lines of the same green full run (1,518 files, 2,170 file-seconds in 440 s wall, effective parallelism 4.9 of 8; `~/code/orderflow` at 0d0f7b78a holds 1,503).

| Kind | Files | Tests | File-seconds | Share | Median file |
|---|---|---|---|---|---|
| App tests under `tests/<area>/` | 1,414 | 20,902 | 1,727 | 79.6% | 0.39 s |
| Build-checks | 67 | 899 | 344 | 15.9% | 1.10 s |
| Scaffold | 16 | 358 | 80 | 3.7% | 0.20 s |
| Scripts | 21 | 455 | 18 | 0.8% | 0.50 s |
| Harness suite (own command) | 36 | 325 | 48.7 s wall | | |
| End-to-end (Playwright) | 92 spec files | 275 on 30 Oct | 282 s wall | | |

There is no database-free "unit" group to time: the harness points every file at a worker database, and a text search finds 916 of 1,503 files importing database code directly. 34 files take 10 s or more: 41% of the file-seconds. End-to-end figures come from the transcripts: 16 readings of 100 tests or more took 126 to 504 s (median 189); 1,094 targeted readings under 30 tests took a median 25 s.

## What `vitest related` would skip

`vitest list --filesOnly --changed` is vitest's import-graph road (`scoped_suite.py` uses it). I ran it in a gate copy made with `make_copy.py`, appending a comment to one file at a time and restoring it, on 40 source files drawn at random from the 176 commits since 1 October.

- A one-file change reaches a median **175 of 1,503 files (12%)**; 25th to 75th percentile 36 to 303; range 0 to 874. By file-seconds the median is 20% of the suite (25th to 75th: 2% to 27%). Three of 40 reach more than half. Build-check and scaffold files appear only when imported (median 0 of 83).
- A typical issue is wider: the median commit changes 4 source files (28 of 176 change one). In batch-d69d80, 20 of 48 scoped calls were wide, over half of all files; the 28 that ran took a median 343 s against 488 s for the whole suite.
- It skips the checks that read source as text. `scoped_suite.py` adds them back for that reason: three finale reds escaped in one early run (its docstring).

## What the numbers imply

Wall time follows file count, not speed per file, and files grew by about 250 a week in October. A full run costs 9 minutes and 2.2 to 2.8 of them happen per issue, so a time budget is met by running fewer files per issue, not by tuning the full run. A single-file change reaches about one file in eight, but a typical issue diff is wide enough that 20 of 48 scoped calls fell back to the whole suite. Flakes are concentrated, five files holding half the rows, and cost seconds since the recheck began.
