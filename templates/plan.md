# <Feature> plan

Feature: <name>
Branch: feature/<name>
Written: <date>

One page. Abdul reads this and nothing else before the run: a line per note, the order, which notes wait for which, and the questions of four kinds. The plan check reads the `Questions` part, the `Rulings` part and the `Approved:` line and nothing else of this file.

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

<Leave this part out until Abdul cuts a note. Then one line per cut note: "<nn> <title>, cut <date>: <why, and where it goes next>". The note file moves to `cut/` in this folder.>

## Rulings

<Leave this part out until a run stops on a note. `rulings.py record` writes each entry, and nobody edits one by hand. One entry per note a ruling changes; the number is `final` for a question of the final check. The kind in brackets is the class the agent typed, `none` or a risk class (`money`, `access`, `migration`, `data leaving`); `re-arm` for a note that failed three strikes; `correction` for a note the note checker corrected; or `follows <nn>` for a note another ruling touched and for a fix note, with the who of the ruling it follows. Who is Abdul's name, `default` or `panel`. An entry by `panel` settles a risk-class question he did not answer: it also carries a `Panel:` line, the count of the three readers and the name of their files, and one `Condition:` line per test the readers who chose the road named, which the note takes as a done check. An entry in his name carries a whole message or a whole sentence he typed after he was shown the note, and a `follows` entry in his name carries the words of the ruling it follows. After the approval, only this part of the page and a `## Cut` line under his own ruling may change. A note or a test may change only in the one commit that adds its entry.>

- [none] <nn>: <the question, in plain words>
  Ruled: <date>, <who>, "<Abdul's words, the agent's written default, or the road a panel's count gives>"
  Touches: <none, or the numbers of the other notes the ruling reader named>
  Undo: <what reversing the ruling costs>
  Confirmed: <date; Abdul's answer at the gate, with his words for a risk class. A ruling he made himself carries no such line; a `follows` entry always takes one.>
- [follows <nn>] <nn>: <what the first ruling changed in this note>
  Ruled: <date>, <who>, "<the edit>"
  Touches: none
  Undo: <cost>
- [money] <nn>: <a question a default answered and Abdul reversed>
  Ruled: <date>, default, "<the default>"
  Touches: none
  Undo: <cost>
  Overturned: <date>, "<Abdul's words>"
  Fix: <the number of the fix note that undoes it>

Approved: <date>
