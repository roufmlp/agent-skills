# What version 1's verify gate found in the browser

Counted on 2026-11-01 for "What the verifier checks in the browser", from Orderflow's verify-gate verdicts at `~/code/orderflow/.scratch/*/runs/*/verdicts/*-verify.md`. Verdict wording varies, so each reject was classified by reading it.

## Counts

- 227 verify verdict files survive: 206 from orderflow-v1 and 21 from request-kinds run batch-d69d80. About 20 early runs kept ledger rows but no verdict files. The ledgers (`run.md`, 73 runs) record 464 verify rounds, 302 passes and 162 rejects.
- 48 of the 227 files are rejects: 46 say REJECT or NOT PASSED, and two (issues 636 and 381) grade a criterion `fault` with correct behaviour.
- 16 rejects name a fault the verifier saw by driving the app. Four more (issue 370, the credit Undo race) came from overlapping clicks, so 20 on a loose count. The other 28 were short written proof or a wrong criterion (about 17), and test, code, doc or build faults (about 11).

## On or off the main flow

Judged by screen name. Of the 16, 11 sit on the main flow: the raise form, the direct order, Confirm, Book delivery, delivery arrival, earlier-date answers and the mock-up revision. Five sit off it: the Setup Products sheet (issue 232), the report-a-problem screenshot (issue 668, two rejects), the bills page (issue 383) and page titles (issue 235c). The Undo race is an admin edge action.

## Did a spec miss it?

In 9 of the 16 the implementer's own spec or end-to-end case passed while the walk found the fault: issues 232, 668 (two), 373 (two), 20, 235c, 599 and 376. The issue 668 case compared only the sidebar's position, so it stayed green over a wrong picture. For the other seven the records show no spec for that path. Almost every miss was a path the spec never took: a second road, a reload, scrolling or a race.

The verifier's walk was itself throwaway Playwright cases with hostile data, written in a private copy after it read the code.

## Time

The `merge-briefing.md` tables hold 379 verify-gate steps in 59 runs: mean 14.0 minutes, median 13.1, 90th percentile 20.8, longest 68.8, with one 538.7-minute outlier left out. No record splits the walk from the rest of the step. The 2026-09-28 performance audit puts the step's tail in its own whole-suite coverage run.

## Examples

- `orderflow-v1/runs/batch-0b441f/verdicts/668-attempt-2-verify.md`: the screenshot drew the top of the page, not what was on screen.
- `request-kinds/runs/batch-d69d80/verdicts/16-attempt-1-verify.md`: the typed total and credit note were lost on reload.
- `orderflow-v1/runs/batch-04dff9/verdicts/232-attempt-1-verify.md`: focus fell to the page body after Down in the Products sheet, so Escape did nothing.
- `orderflow-v1/runs/batch-2e6652/verdicts/599-attempt-1-verify.md`: "Did it arrive?" was drawn twice per booking.
