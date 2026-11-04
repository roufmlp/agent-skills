Status: resolved
Type: research

# How long Orderflow's test suite takes, and where it flakes

## Question

Abdul says the full suite in Orderflow takes about ten minutes per issue, often more than once, and that flaky tests force reruns. Orderflow's `vitest.config.ts` puts `npm test` at about 197 seconds on 8 workers. Measure the gap from the version 1 run records and transcripts: how long each full run took and how it grew from September to October, how many runs each issue made, how many failures passed on a rerun with no code change, and which test files those were. Also count the tests by kind (unit, build-check, scaffold, harness, end-to-end) and the time each kind takes, and say which ones `vitest related` would skip for a typical one-file change. "How the careful lane keeps the test suite fast and trusted" waits on these numbers.

## Answer

Abdul's ten minutes are right, and the 197 seconds were right when written: the suite grew. The comment in `vitest.config.ts` dates from 29 September, at 516 files. The last run, batch-d69d80 on 30 and 31 October, took a median 488 seconds on 1,518 files, plus a median 51 seconds for the harness suite, so 9.0 minutes a run. The weekly median doubled in four weeks, from 202 to 410 seconds, while files grew 2.5 times. Each issue ran 2.8 whole suites in the map's window and 2.2 in the last batch.

Flakes cost less than they feel. The flake ledger holds 261 failures since 3 October that passed when the file ran alone on the same tree, spread over 57 files, with five files holding 54% of them. At most one whole-suite run in four hit one, and in the last batch 2 of 24, each settled in seconds by the recheck. Before the recheck existed, a flaky red cost a whole-suite rerun of about four minutes.

App tests take 80% of the suite's file-seconds and build-checks 16%. Every file runs against a worker database, so there is no fast database-free group to split off. `vitest related` would cut less than hoped: a one-file change reaches a median 12% of files, but a typical issue changes four source files, and in the last batch 20 of 48 scoped runs reached more than half the suite. Those scoped runs took a median 343 seconds against 488 for the whole suite.

The figures, their sources and the gaps (no flake data before 3 October, and only one run's wrapper records still on disk) are in [the test suite research](../research/20-orderflow-test-suite.md).
