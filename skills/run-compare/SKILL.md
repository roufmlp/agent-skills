---
name: run-compare
description: Answer whether the pipeline is getting cheaper, faster or better across runs, from the records every finale writes. Use for "was that run cheaper", "is the pipeline getting faster", "how did this run compare", "what changed since the last run", "how many faults escaped", "what did the last hunt cost", or any question about a run or a hunt measured against the ones before it.
argument-hint: "a question, or nothing for the last line of each kind"
---

# Run compare

Answer one question about the pipeline, in words, over figures `run_compare.py`
prints. Ticket 37 of the pilot-delivery map, rulings 22, 25 and 26.

**The script is the fact. This skill is the sentence.** `run_compare.py` holds
five fixed subcommands and every figure comes from them. Run the one that
matches the question, read what it prints, and answer.

## The one rule that shapes everything else

It reads. It **never writes and never measures.**

`run_costs.py` at a finale is the only writer of `runs.jsonl` and
`issues.jsonl`, and `run_records.write_view` the only writer of the generated
page. A reader that wrote would make asking a question change the answer; a
reader that opened a transcript would be a second measurer of a quantity
`run_costs.py` already measures, and two readers of one quantity drift apart.

So: no transcript is opened here, and no arithmetic is done on a figure the
script did not print. It answers in the session it was typed in, on that
session's model, spawning nothing (ruling 26).

## Steps

1. **Pick the subcommand from the question.** One run each; the table below is
   the whole map.
2. **Run it** from the repository holding `.scratch/workflow-audit`:

   ```
   python3 ~/.claude/skills/run-issues/run_compare.py <subcommand> [--repo <path>]
   ```

3. **Read its whole output**, including the lines saying what it skipped. A
   skip is a finding.
4. **Answer the question asked**, in the words the next section allows.

## Which subcommand answers which question

| The question | Run |
|---|---|
| How did the last run go? What changed? | `run_compare.py last` |
| How did run X go? | `run_compare.py show <batch-id>` |
| What has the last fortnight looked like? | `run_compare.py since <days>` |
| Was run X cheaper than run Y? | `run_compare.py compare <a> <b>` |
| Which runs ran the same pipeline? What changed between them? | `run_compare.py versions` |

`last` reports the newest line of each kind — a run and a hunt — each against
its own predecessor. Start there when the question names no run.

## The words this skill may use

**Figures, directions, and one judgement.** Ruling 25 fixes the range:

- **Figures**, as the script prints them, in its units.
- **Directions**: up, down, level, and by how much, against the previous line
  of the same kind.
- **One judgement**: a figure the script names as outside its **observed
  range** is repeated as that, and no further.

**No cause and no advice.** Say what moved. Do not say why it moved, and do
not say what to do about it. Both are the human's, and a reader that guessed at
either would be answering a question nobody asked from a record that holds no
evidence for it. The issue mix is not controlled across runs, so a difference
of a few per cent is the batch rather than the change.

**One threshold exists and the script owns it**, on the cache read-to-write
ratio (ruling 14). Where the script prints that alarm, carry it whole. Where
it prints none, there is none: every other figure is direction and range.

**A null is not a zero.** `not measured` means nothing read the figure. Report
it as a missing measurement, never as a clean run and never as a zero.

**A skip is reported.** The script says which lines it skipped and why —
lines marked `borrowed`, lines carrying no count, a register whose tables
declare no `origin` column. Carry those sentences into the answer. A trend
read over lines nobody was told about is the fault this whole ticket exists
to end.

## Where the fuller picture lives

`.scratch/workflow-audit/run-costs.md` is the one-look page (ruling 13): the
per-run table, the per-issue table, and the longest steps by kind. It is
generated from the records, so point at it rather than copying it out. Name it
when the question wants more than the four directions.
