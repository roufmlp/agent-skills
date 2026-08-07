# Glossary — the words `parallel-hunt` uses

Fifteen terms. A stranger reading the skill meets most of them with no definition
anywhere, so they are defined here once and used the same way everywhere in the pack.

Nothing here is a rule. The skill beside this file holds the rules, and the decision
record beside it holds the reasons behind them.

## The roles

**Orchestrator** — the single session that runs a round from launch to close. It
spawns the workers, reads statuses, and writes the report. It stays deliberately
ignorant: it does not read evidence or diffs, because its context is the only one
that has to last the whole round, and an orchestrator forming opinions about bugs is
an orchestrator that has stopped being thin.

**Finder** — a worker that hunts one sweep group of the live system for real
defects. It writes evidence and a failing test for each one, and it never touches
shipped code. Its failure mode is silent: a defect it misses is found weeks later by
a human, not by anything downstream.

**Fixer** — a worker that takes findings in order and fixes them test-first. It owns
shipped code, fakes and fixtures. It runs at the same time as the finder, on the
same branch, which is why the ownership line between them is drawn hard.

**Claim gate** — a short-lived reviewer that tries to refute a finding rather than
confirm it, and either lets it through to be fixed or retracts it. It exists because
a false finding costs more than a missed one: it buys a fixer's time, a gate's time,
and it leaves something untrue in a file that later work trusts.

**Fix gate** — a short-lived reviewer that tries to refute a fix. It asks whether
the fix addresses the cause or hides the symptom, and whether the test would still
fail if the defect came back. A variant of it grades fixes that touch money,
authentication or secrets against a stricter rubric.

**Promotion** — the closing role, run once at round end, and the only one in the
loop that writes an issue file. It resolves every register row on a stated rule —
into an issue, a refusal, or out as fixed — and it decides on the row alone,
reading no evidence, so a row that cannot be judged by its own contents is refused
as faulty rather than investigated.

## The units of work

**Round** — one whole hunt, from launch to close. It ends when the finder comes back
empty twice and nothing is left part-fixed.

**Sweep group** — one finder's slice of a round: a subsystem, or a small number of
new findings, whichever it reaches first. It is sized so the worker finishes before
its context degrades rather than after.

**Batch** — one fixer's slice: a few findings carried through to a fix a gate can
review. Same reasoning as a sweep group, different worker.

**Brief** — what a round is about. The scope it covers, the sweep groups it is cut
into, and why it was called. It belongs to one round and is thrown away at close,
because a round that has ended has nothing left to tell the next one.

## The records

**Register** — the index of live findings, one line each. It is a table and nothing
more: every worker reads it to decide what to do next, so weight in it is weight
every worker pays for. It does not rotate and it is never archived. Three exits empty
it — a finding is promoted into the project's issue tracker, it is refused and
dropped, or it leaves as fixed because the round already fixed and verified it.
What remains is what is still waiting, so its length is a number worth reading.

**Row** — one finding's line in the register: an identifier, a one-line summary, who
can see the fault, how bad it is, where it has got to, and a short pointer to its bug
file. The last cell is capped, because it is where prose collects and prose is what
makes a register unreadable. Anything longer belongs in the bug file.

**Bug file** — one file per finding, holding the evidence, the reproducer, the test
path and every gate's verdict. It is where the fixer reads and where the gates write.
Everything a row cannot hold lives here, and there is no length limit.

**Ruling** — a decision the orchestrator makes during a round that later work must
respect: a boundary redrawn, a class of finding declared out of scope, a judgement
between two workers' claims. A ruling outlives its round, so it is written down where
the next round will find it rather than in the round's own brief.

**Lead** — something worth looking at that nobody has looked at yet, or a place
already examined and found clean. Leads outlive rounds too: their value is stopping
the next finder walking ground the last one covered. They accumulate, so they are
harvested by hand rather than left to grow, and the harvest sorts each one by how
widely it is true — of a tool anywhere, of this product only, or of one file at one
version.
