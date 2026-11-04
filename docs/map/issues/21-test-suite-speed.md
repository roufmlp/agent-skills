Status: resolved
Assignee: Abdul (wayfinder session 2026-10-31)
Type: grilling
Blocked by: 20

# How the careful lane keeps the test suite fast and trusted

## Question

Every careful-lane change passes "tests and typecheck", and in Orderflow that step grew to about ten minutes per issue with reruns for flaky tests. Decide what a build session runs while it works and what it runs once before the merge (for example `vitest related` during the work and the full suite once per note), what happens to a test that fails and then passes with no code change, and whether a budget refuses a suite that grows past a set run time. Parallel notes share one laptop, so decide too how several sessions running suites at once stay inside its limits; "How a feature with several change notes runs without Abdul" settles how many run at once. "How the careful lane keeps every slice aligned to the core design" adds about 10 seconds of pattern and module checks and a minute of screenshots per change; they are part of the suite this ticket sizes.

Changed by "How long Orderflow's test suite takes, and where it flakes" (2026-10-31): the full suite took 9.0 minutes a run at the end of October and doubled in four weeks; each issue ran it 2.2 to 2.8 times. Flakes hit at most one run in four, and a recheck of the failing file settles them in seconds. `vitest related` saves less than expected, because a typical change reaches a large share of the suite. Growth, more than flakes, is the problem this ticket has to solve.

Changed by "How a feature with several change notes runs without Abdul" (2026-10-31): at most three notes of one feature and at most two features run at once, so up to six build agents can share the laptop; this ticket may raise or lower both numbers. Each note's verifier runs the tests, and after the last note merges a final verifier runs the full suite, the typecheck and every baseline screenshot on the merged branch. Version 1 measured one suite at 6,120 seconds beside a second run against 591 seconds alone.

## Answer

Most notes never run the full suite. The implementer runs the test files it writes or changes, the note's verifier runs one scoped run, and the final verifier runs the full suite once on the merged feature branch. A feature of three notes then costs about one full run, where version 1 spent seven or more at 2.2 to 2.8 per issue. The price is that a note can break a test outside its scope and only the final check sees it. The final check already gives a fresh implementer one round to fix its findings, and git shows which merge did the damage.

**What runs when.**

| Who | Runs | Time on Orderflow today |
|---|---|---|
| Implementer | The test files it writes or changes | Seconds |
| Verifier | `vitest related` on the note's diff, the checks that read source as text, the pattern and module checks, and the end-to-end specs and screenshots of the screens the note changes | Median 343 s for the scoped run |
| Final verifier | The full suite, the harness suite where a product has one, the typecheck, every end-to-end spec and every baseline screenshot | 9 minutes and more |

This replaces "tests" in the verifier's row of "How a feature with several change notes runs without Abdul" with the scoped run. The pattern and module checks from "How the careful lane keeps every slice aligned to the core design" take about 10 seconds, so the verifier runs all of them every time.

**Flakes.** A failing file runs again alone on the same tree, up to five files. If it passes, the run is green and the suite script writes a row to the product's flake ledger. The audit's monthly table gains a row naming the three files with the most flake rows, and the audit may propose a change note to fix them. Nothing quarantines or skips a test by itself, because a skipped test can hide a real bug. Dropping the recheck would bring back the four-minute full rerun that each flaky red cost before October.

**Suite budget.** Each product's `CLAUDE.md` names a suite budget: the longest a full run may take. A new product starts at 5 minutes; Orderflow starts at 10, against 9.0 today. The final verifier writes the full-run time in the feature report. When the last reading is over budget, the next `/build-feature` interview puts one more question on Abdul's page: raise the budget, or add a pruning note first that merges or deletes duplicate tests. Nothing stops mid-run. A hard limit would stop runs at night over growth that many notes made together, and no budget at all is what let Orderflow's suite double in four weeks.

**Sharing the laptop.** One machine lock covers full suites and full end-to-end runs, so only one runs at a time and the rest wait. Scoped and single-file runs skip the lock and use at most two workers each. The limits stay at three notes per feature and two features at once, six build agents at most. Since only final verifiers run full suites, the lock rarely holds anyone up. Version 1 shows why it matters: one suite took 6,120 seconds beside another, against 591 alone. Splitting the workers without a lock keeps the database contention, and locking every run queues a scoped run behind a nine-minute full one. The audit already counts the most sessions running at once, and the limits rise only when it shows spare capacity.

**The script.** The plugin ships one new suite script of about 150 lines in place of the 1,002 lines of `run-issues/run_suite.py`. It takes the lock for a full run, runs the test command that the product's `CLAUDE.md` names, rechecks failing files and writes the ledger, and records the run time. Every verifier calls it and none runs the test command directly, because a brief that tells an agent the rules is a reminder, and reminders fail. The script counts against the plugin budget from "How a regular audit keeps the workflow small". This is a default.

The facts behind this answer are in [the test suite research](../research/20-orderflow-test-suite.md) and the `take_lock` docstring in `run-issues/run_suite.py`.

`CONTEXT.md` now defines flake and suite budget.

Changed by "Whether the build agents work test-first" (2026-11-01): the suite script also runs the red check, which runs each new vitest test against the code from before the note. The implementer runs it before it hands over, and the verifier's scoped run runs it again as the refusal.

Changed by "What the verifier checks in the browser" (2026-11-01): after the scoped run the verifier runs a hostile walk of the note's actions. A walk case that finds a fault becomes a spec in the fix; the rest are thrown away, so the suite grows only by faults found.
