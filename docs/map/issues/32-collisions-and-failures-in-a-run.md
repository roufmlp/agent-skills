Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: grilling
Blocked by: 25

# What a run does when notes collide or fail

## Question

[The walkthrough](../research/25-walkthrough.md) ran ten change notes for "Report a problem" through `/build-feature`, with five migrations and one note that took three strikes in version 1. It found five gaps, C5 and C8 to C11.

The red check restores "the source files from before the note", but does not say whether a new migration is source or how the test database is rebuilt. Keep the migration and a row-rule test passes on the old code and is refused; drop it and every database test fails at load. Two notes running at once both take migration 0077 under different names, and git merges both with no conflict and no strike. After a note fails three times, nothing says whether it retries, who rewrites it, whether Abdul approves the rewrite, or whether the final check runs on the notes that did merge; version 1's carve has no successor. The final check tests the feature branch, then the merger merges into a local main that moved during a run of several days. And the fresh implementer that fixes final-check findings has no "before the note", so the red check and the hostile walk skip its work.

Decide each of the five.

The lighter option: a note's migration counts as source and the test database is rebuilt from main's migrations; a note with a migration waits for every earlier note with one; a third failure stops that note, keeps the merged ones and puts the rewrite in the next interview; main is merged into the feature branch before the final check; the final fixes get a red check against the branch head. A heavier answer says what this would cost.

Changed by "Whether version 2 is built in two stages" (2026-11-01): this ticket belongs to stage two, the careful lane. It is grilled on paper while stage one runs.

Changed by "What the interview settles before a run" (2026-11-01): Abdul asked whether two features running at once collide. Each has its own folder and its own worktree, so their notes, plans and reports never meet, but two features can still change the same code file or take the same migration number. The answer here covers notes of different features as well as notes of one feature.

## Answer

Abdul took the lighter option on four of the five gaps and a merge-time number on the fifth, on 2026-11-01. Nothing here adds a hook or a role; the suite script, the merger and the `/build-feature` skill each gain a few lines.

**A note's migration is source (C5).** The red check puts back the note's migrations along with its code, and every check run builds its test database from empty, from the migrations on disk. Orderflow's `scripts/migrate.mjs` records each file by name and never undoes one, so a database that has seen the note's migration keeps its table after the file goes; only an empty database shows the code from before the note. A test that cannot find its table fails, the same as a test whose module does not exist, which "Whether the build agents work test-first" already counts as a fail. Keeping the migration would have refused every sound row-rule test, because Orderflow's row rules live in the migration. Building from empty has not been timed; Orderflow has 91 migrations today, and the build session measures it.

**Migration numbers are set at the merge (C8).** A note writes its migration with whatever number is next on its own branch. Before the merger merges a note into the feature branch, it gives the migration the next free number there, and a check refuses two migrations with the same number. The same step runs when local main merges into a feature branch, below, so two features that both took `0092` come out as `0092` and `0093`. Renumbering is safe because no migration reaches production before Abdul's push, and because every check builds its database from empty. A note whose migration depends on another note's already waits for it through its "Waits for:" line. The lighter option, making each note with a migration wait for every earlier one, would have run five of the walkthrough's ten notes one at a time and still needed this check for two features. "Where the note check lives, and baselines for changed screens" decides where the check lives. A renumber that meets a staging database which already has the old name rebuilds staging from seed; this is a default.

**After a third failure (C9).** The feature does not merge and the final check does not run. When Abdul types `/build-feature <name>` again, the skill sees the failed note in the report and opens a short interview instead of the run. Claude reads the failure reports and offers two roads for each failed note: change it, or cut it. Abdul may also cut notes that already merged, if he would rather ship them later; the merger reverts each cut note's merge commit on the feature branch. A note that waits for a cut note, or uses its work, is cut too or changed, and the interview lists those before he approves. He approves the changed plan, and the run carries on. Merged notes that stay are never built again. A changed note starts with three new strikes. A cut note becomes a one-note change or part of a later feature. The final check runs once, on the whole feature, when no note is left to run. Retrying the same note unchanged would repeat the failure, and merging the finished notes without the final check would drop the only reader of the whole feature.

**The final check meets the current main (C10).** Before the final check, the merger merges local main into the feature branch. A conflict it cannot resolve is a final-check finding and goes into the one fix round. The merge into main is fast-forward only; if main moved after the final check, the merger merges it in again and the final check runs again. This also covers two features that change the same code file: the one that finishes second sees the first one's code before its final check.

**The final fix round gets a red check (C11).** The fix round's "code from before" is the commit the final check tested. Each new test from the fix must fail there. No hostile walk is added: the final verifier already runs every end-to-end spec and every baseline again, and the fixes this round makes are usually between notes rather than on screens, as the walkthrough's migration-order fix was.

`CONTEXT.md` now defines cut, and the red check covers migrations.

Changed by "Where the note check lives, and baselines for changed screens" (2026-11-01): the duplicate-number check runs in the `pre-commit` and `pre-merge-commit` git hooks of each graduated repo.
