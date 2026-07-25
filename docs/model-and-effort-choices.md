# Picking models and effort for a multi-agent run

*Written 25 July 2026, the day after Claude Opus 5 shipped.*

These two skills spawn a lot of subagents. A single nineteen-issue run of
`run-issues` produced around fifty-seven of them. So two questions decide most of
what a run costs and most of what it catches: **which model runs each role**, and
**how hard that role is told to think**.

For four months I answered both from documentation. This is what happened when I
measured instead.

---

## The table that never did anything

The skill carried a roles table. Each role had a model and an effort level, with
rules for raising the effort on riskier work — a review gate went to `max` when
the diff touched money or authentication, the end-of-run coherence pass ran at
`max` always. There was a `--effort=max` flag on the command.

None of it took effect.

The `Agent` tool that these skills use to spawn workers accepts a `model`
parameter. It does not accept an effort parameter. There were no agent definition
files in the setup, so every subagent inherited one session-wide `effortLevel`
from `settings.json`, set to `high`. The table described intentions the harness had
no way to honour. `--effort=max` changed a line of prose in a prompt and nothing
else.

That is a mundane bug, but it had an expensive shape: decisions kept being made
*against* those numbers. "Review-gate effort floors were examined and deliberately
left unchanged," says one revision note. Examined against what?

## Testing the mechanism instead of trusting it

The `Agent` tool's own documentation says an agent type's model, reasoning effort
and tools come from its definition file's frontmatter. Three other signals said
otherwise: the tool's parameter schema has no effort field, the community agent
validator doesn't know the key, and an agent file with `effort: banana` loads and
runs without complaint.

Three to one against. So the null hypothesis was that the key is silently ignored
and every probe would come back at the session default.

Two agent files, identical apart from one line. Same model, same tools, same
prompt, same task — enumerate the edge cases of an ISO-8601 duration parser.
Interleaved runs so API load couldn't drift between conditions, and a control with
no effort key at all to establish where the session default sits.

| rung | mean wall-clock | vs default | mean output words |
|---|---|---|---|
| `low` | 40.7s | — | 371 |
| **`high` (session default)** | **39.7s** | baseline | 382 |
| `xhigh` | 48.7s | **+23%** | 506 |
| `max` | 73.3s | **+85%** | 476 |

The key is live. `max` runs twice as long as an otherwise identical agent whose
only difference is that word.

**And `low` is indistinguishable from `high`.** That was not the expected result.
The published ladder has five rungs; on this task only the top three separate. My
guess is the task — enumerating edge cases is recall, not chained reasoning, and a
low-effort model can still list things — but a guess is what it stays, because
that's what the measurement supports. The practical consequence is that the usable
dial here is `high → xhigh → max`, and there's no evidence that dropping a role to
`low` saves anything.

## The model question, which I could not settle

Model pinning by family works. An agent file with `model: haiku` reports being
Haiku, consistently.

Version is another matter. Three probes returned three different answers —
"Opus 4.8", "Opus", and "Claude Opus 4.5". Models are unreliable narrators about
their own version, which makes self-report worthless as evidence, so I can't tell
you what the `opus` alias resolves to. I'm not going to publish a claim I couldn't
support.

The workaround is to not need the answer: every agent file uses `model: inherit`,
so workers run whatever the session runs, and pre-flight asserts the session model
before anything spawns. That trades a question I couldn't answer for a check I can
actually perform.

## Where the money actually is

Worth stating plainly, because I spent longer on the effort question than it
deserved.

A long run's cost is dominated by **output tokens** — thinking plus generated code.
Moving the routine gates from the most expensive model to one at half the price
roughly halves the run. Raising effort a rung adds tens of percent to the output
side. Context re-read across spawns — the ledger, the primer, the briefs — is a few
hundred thousand *input* tokens, which is pennies, and near-free once it caches.

So: **model choice is first-order on cost. Effort is second-order. Context is
third-order on cost but first-order on quality**, because a bloated shared file
doesn't show up on the bill, it shows up as decisions being re-litigated against
stale state.

That last one is worth an example. The run ledger in this skill is read by every
spawn. On one run it reached 39,800 characters, 23,000 of it a log of what had
happened — twenty-five entries averaging nine hundred characters against a rule
that said "about two lines". The fix at the time was a stricter rule. It failed
twenty-five times out of twenty-five, because the log lived in the file everyone
reads and the rule asked a busy runner to remember to prune it.

The fix that stuck was structural: the log moved to a separate journal that
subagents never open, and the ledger became a status table and nothing else. Two
rules deleted, and the failure mode became unrepresentable rather than forbidden.

## What changed in the skills

- **The top-tier model left the routine path.** It had been the review gate, both
  hunt gates, the coherence finale and the escalation, on the theory that
  adversarial judgement was its strength. Anthropic's own comparison now puts the
  cheaper model ahead on agentic coding, agentic search and knowledge work — which
  is what those roles do — at half the price. Then a probe found the account's
  credits for it were exhausted, which made the point moot: a break-glass model
  that isn't there when you break the glass turns a hard issue into a halted run.
  Escalation is now the same model at `max`, a measured +85%.
- **Briefs moved out of the skill and into eleven agent definition files.** The
  runner no longer pastes a brief into every spawn; it names an agent type. Each
  file carries its own role, model and effort, and is loaded only when that role
  runs. The skill dropped by more than half.
- **Conditional escalation became real.** An agent file has one fixed effort, so
  "raise to max when the diff touches money" can't live inside one file. It became
  a second agent type that the runner chooses. A rule nobody could enforce turned
  into a branch.
- **Gates now derive a rubric before judging.** Each gate turns the acceptance
  criteria into numbered, independently checkable statements, writes them into its
  verdict, and marks each one against cited evidence. A criterion with no evidence
  is a fail — "I didn't see a problem" is not verification, and that's how
  half-finished work used to pass.

## What I'd tell someone doing the same

Measure the mechanism before you tune it. I spent months adjusting numbers in a
table that the harness never read, and the tell was there the whole time: the
parameter simply wasn't in the tool's schema.

And when the documentation and the evidence disagree, the cheap move is usually a
two-minute experiment rather than a longer argument with yourself.
