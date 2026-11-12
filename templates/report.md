# <Feature> report

Feature: <name>
Branch: feature/<name>
Started: <date>
State: <running, stopped, held or merged>
Merged: <date> <merge commit on local main; this line exists only once the feature is in main>
Last change: <date and time; the watchdog reads this file's mtime, this line is for Abdul>

The merger writes this file on the feature branch after every note, and the final verifier and reviewer add their parts. It is the run's ledger: a later `/build-feature <name>` reads it, skips the merged notes and carries on. `/build-feature` refuses a feature whose report on local main carries a `Merged:` line.

## Notes

One row per note. State is one of `not started`, `running`, `merged <commit>`, `failed`, `stopped: <the question>`, `stopped: tooling: <tool>: <its line>`, `waiting: <why>` or `cut <date>`. A `failed` or `stopped:` row takes a ruling and the run starts again. A `waiting:` row has no timeout: only Abdul rules on it, and the notes that do not wait for it run on. A question of the final check has a row of its own, `final`, below the notes: `stopped: <the question>`, `waiting: <why>`, or `ruled <date>` once it has its entry; no final check runs while it stops or waits. `State: held` means the final check passed and rulings made without Abdul wait for his answer before the merge.

| Note | State | Strikes | Attempts | Last report |
| --- | --- | --- | --- | --- |
| 01 | merged <commit> | 0 | 1 | |
| 02 | failed | 3 | 3 | <path of the last reject report> |
| 03 | not started | | | |

## Roles

| Role | Model | Effort | Tokens | Cost | Strikes |
| --- | --- | --- | --- | --- | --- |
| implementer | <model> | <effort> | <n> | <$> | <n> |
| road finder, <nn> | <model> | <effort> | <n> | <$> | |
| panel readers, <nn> | <model> | <effort> | <n> | <$> | |

<One row per role of the run. `feature_run.py roles` fills the tokens and the cost, and adds the last two rows for each risk-class question a panel judged: its road finder, and its three readers together. A note's second such question is `<nn> (2)`.>

## Time

Full suite: <seconds> s against a budget of <seconds> s (<over or under> budget)
Run: <started> to <ended>, <hours> h

## Defaults taken

<One line per default a build agent took mid-run, with the note number. A default that is hard to undo is a stop instead: the note's line is under "Decide" below.>

## Done-check edits

<One line per done-check file an implementer edited, with the note number and why. The reviewer reads each against the note.>

## Final check

Door: <two-way, with the rollback in a clause; or one-way, with what cannot be undone>
Blast radius: <who or what breaks if this is wrong: one word, then a clause>

<The final verifier's and final reviewer's findings, each fix round that ran, three at most, with every finding of both roles in one batch, and the pre-launch gate steps 1 to 7 with a result each. A finding that needs a new test is a `Fix note needed:` line: the session writes the fix note, and no fix round adds a test.>

## Screens

<Each new screen at 390 and 1280 pixels, and each changed screen before and after with each difference marked. The side-by-side page's layout.>

## Decide

<One line per note that stopped on a question, with the class, the question and the agent's written default: `<nn>: [<class>] <question> Default: <default>`; `final:` opens a line of the final check. The class is the one the agent typed, `none`, `money`, `access`, `migration` or `data leaving`, and `unclassified` when it typed none: that one waits for Abdul. The session rules on each: Abdul's answer, or once the wait is over the default for a class of `none` and a panel's count for a risk class. A line stays while its row stops or waits. A line `<nn>: [correction] <what the note checker corrected>` stays for good: the plan check counts it against the plan's `[correction]` entries.>

## Tooling stops

<One line per step a tool refused: `<date> <nn or final>: <hook, check script, desktop app or other>: <the refusal line>`. A tool fault is not a question. The weekly audit counts these lines by family.>

## Ruled while you were away

<One line per ruling Abdul did not make and has not confirmed, a correction by the note checker and every `[follows <nn>]` entry included: the note, the question, the road taken, who took it, the notes it touched and the undo cost. A risk-class line opens with its class in bold capitals. A panel's line also carries the count, each reader's vote and reason, the conditions, each found road marked "a road the question did not offer" with its evidence and undo cost, and each candidate road with the fact it needs from him. The feature stays off local main until each has a `Confirmed:` or `Overturned:` line on the plan page.>
