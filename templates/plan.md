# <Feature> plan

Feature: <name>
Branch: feature/<name>
Written: <date>

One page. Abdul reads this and nothing else before the run: a line per note, the order, which notes wait for which, and the questions of four kinds. The plan check reads the `Questions` part and the `Approved:` line and nothing else of this file.

## Notes

| Note | What it does | Migration | Waits for | Screens |
| --- | --- | --- | --- | --- |
| 01 | <one line> | <none, or what it adds> | none | <none, names, or all <group>> |
| 02 | <one line> | none | 01 | <...> |

## Order

<Which notes start together, three at most at once, in the order the `Waits for` column gives. One line per round: "Round 1: 01. Round 2: 02, 07, 08.">

## Questions

One line per question, then its answer on the next line, written as Abdul gives it. A question with no answer holds the plan. The kinds, each written in brackets as shown:

- [core design] <nn>: <the pattern a note adds, or the screens it rewrites, and what the check behind it is>
  Answer: <Abdul's words>
- [migration] <nn>: <what the migration adds; it may only add>
  Answer: <Abdul's words>
- [money or access rules] <nn>: <the rule that changes: a price, a right, a row policy, a role, a secret>
  Answer: <Abdul's words>
- [data leaving] <nn>: <what leaves the product or what public contract it commits: a route, a webhook, a push, an email format>
  Answer: <Abdul's words>
- [pruning] suite: <the last full run took <n> s against a budget of <m> s. Raise the budget, or add a pruning note first that merges or deletes duplicate tests?> (only when the last full run is over budget)
  Answer: <Abdul's words>

## Cut

<Leave this part out until the short interview after a failed note cuts one. Then one line per cut note: "<nn> <title>, cut <date>: <why, and where it goes next>". The note file moves to `cut/` in this folder.>

Approved: <date>
