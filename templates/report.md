# <Feature> report

Feature: <name>
Branch: feature/<name>
Started: <date>
State: <running, stopped or merged>
Merged: <date> <merge commit on local main; this line exists only once the feature is in main>
Last change: <date and time; the watchdog reads this file's mtime, this line is for Abdul>

The merger writes this file on the feature branch after every note, and the final verifier and reviewer add their parts. It is the run's ledger: a later `/build-feature <name>` reads it, skips the merged notes and carries on. `/build-feature` refuses a feature whose report on local main carries a `Merged:` line.

## Notes

One row per note. State is one of `not started`, `running`, `merged <commit>`, `failed`, `stopped: <why>` or `cut <date>`.

| Note | State | Strikes | Attempts | Last report |
| --- | --- | --- | --- | --- |
| 01 | merged <commit> | 0 | 1 | |
| 02 | failed | 3 | 3 | <path of the last reject report> |
| 03 | not started | | | |

## Roles

| Role | Model | Effort | Tokens | Cost | Strikes |
| --- | --- | --- | --- | --- | --- |
| implementer | <model> | <effort> | <n> | <$> | <n> |

## Time

Full suite: <seconds> s against a budget of <seconds> s (<over or under> budget)
Run: <started> to <ended>, <hours> h

## Defaults taken

<One line per default a build agent took mid-run, with the note number. A default that is hard to undo is under "Decide" in `~/.claude/pending.md` instead, and this part names it.>

## Done-check edits

<One line per done-check file an implementer edited, with the note number and why. The reviewer reads each against the note.>

## Final check

Door: <two-way, with the rollback in a clause; or one-way, with what cannot be undone>
Blast radius: <who or what breaks if this is wrong: one word, then a clause>

<The final verifier's and final reviewer's findings, the fix round if one ran, and the pre-launch gate steps 1 to 7 with a result each.>

## Screens

<Each new screen at 390 and 1280 pixels, and each changed screen before and after with each difference marked. The side-by-side page's layout.>

## Decide

<Each question the run put under "Decide" in `~/.claude/pending.md`, by heading.>
