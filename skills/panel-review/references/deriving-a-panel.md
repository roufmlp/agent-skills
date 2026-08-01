# Deriving a panel

Two worked derivations, one from each end of the range. Both run the same rule with
no branch: **enumerate the distinct ways this artefact can be wrong, then name who
pays for each. One distinct exposure, one persona** — the same payer can hold several
seats, as example A does twice.

Read this before deriving a panel. The point of the two examples is that neither is
a template — they are outputs of the rule, shown so the rule reads as a method
rather than an abstraction.

---

## Example A: a multi-agent workflow design

The artefact: a proposed design for a skill that implements tracker issues
autonomously, gates each one, and resumes after interruption. Several files plus the
repo it runs on.

| Goes wrong | Who pays | Persona |
|---|---|---|
| Issue built, but not the thing the issue asked for | whoever filed it | requirements owner |
| Passes the gates, breaks when actually run | the verifier, then the user | runtime verification lead |
| Subtly wrong code accepted; costs three months later | the next maintainer | adversarial reviewer |
| One blocked issue stalls nine independent ones | the human, in wall-clock | scheduling engineer |
| Run dies at the usage limit, resumes wrong | whoever restarts it | recovery engineer |
| Bill is several times the estimate | the human, in money | cost engineer |
| Six gates where two would do | the human, in complexity | simplification reviewer |
| **Design is correct but an agent cannot follow it** | the implementer | **the stranger** |

Eight, and the last one is the stranger every panel seats.

### Where the merge rule bites

A hand-written panel for this artefact will almost always include an *adversarial
workflow skeptic*, briefed to attempt partial promotion, hidden dependencies, an
unnecessary global halt, verification of the wrong commit, duplicate work on resume.

Every one of those already belongs to a payer above. Partial promotion is the
reviewer's. The global halt is the scheduler's. Duplicate resume is the recovery
engineer's. The skeptic quotes the same lines for the same reasons, so under rule 2
it is not a perspective at all — it is a *stance* that got split into a seat.

Delete the seat, make the stance mandatory for every persona (rule 3). The
adversarial pressure now runs across all eight angles instead of being concentrated
in one slot that duplicates six of them, and a seat is freed for an angle nobody
holds.

### Scenarios and invariants from the same list

Each failure mode owes one concrete case, and its negation is an assertion:

| Failure mode | Scenario (walked) | Invariant (asserted) |
|---|---|---|
| partial work reaches the branch | issue 07 is rejected on the third attempt after two commits exist | a rejected issue has no promoted code |
| one blocker stalls the rest | issue 04 blocks; 05 depends on it, 06 does not | an independent issue never waits on an unrelated blocker |
| resume duplicates work | the run dies after the gate passes but before the ledger is written | resume produces no second commit for a passed issue |

Note what the invariant check can and cannot do. Reading establishes that a
mechanism is **present and coherent**, and cites where. Whether it **works** needs a
run, and that mark is `UNTESTABLE BY READING` plus the experiment.

---

## Example B: a post announcing a public repository

The artefact: a few hundred words of copy, one file.

| Goes wrong | Who pays | Persona |
|---|---|---|
| Nobody stops scrolling | a stranger, two seconds | the "so what" reader |
| Read but disbelieved; claims sound inflated | someone who has built the same thing, by discounting the author | sceptical practitioner |
| Lands with the wrong crowd | the author | the person they actually want reading it |
| **Understood, but nobody can act on it** | **the reader who wants to try the thing** | **the stranger** |
| Reads like a machine wrote it | the author, in credibility | writing editor |

Five, and again the stranger is the seat an expert panel would have missed: every
other persona judges whether the post is *good*, and only the stranger asks whether a
reader who is now convinced can work out what to do next.

### Scenarios and invariants, same rule

| Failure mode | Scenario (walked) | Invariant (asserted) |
|---|---|---|
| reads as inflated | a practitioner reads the first two lines and stops | no claim outruns what the linked repo shows |
| lands with the wrong crowd | the reader is hiring for an unrelated role | the post names who it is for by the third line |
| nobody can act | a convinced reader has thirty seconds and one tab | the next step is stated, not implied |

"No claim outruns what the repo shows" is the same object as an invariant on a
system design. It reads as a code concept only because the vocabulary arrived from
there.

### The additive-lens trap, in its original costume

A search-visibility persona on career copy is structurally tempted to invent
keywords: its lens is satisfied by adding material, so it proposes terms the
artefact's facts do not support. This is not a career-copy quirk. A reliability
persona on a system design wants three gates nobody needs; a risk persona wants a
caveat on every sentence. Same failure, different costume, and the hard rule covers
all three: propose only material the artefact already supports, and name what the
addition costs.

---

## A third case, for calibration: a small decision

Not every artefact needs a table. A reversible choice with a narrow blast radius —
which of two libraries, what to name a module — routes to `quick`: three personas,
no corpus, no invariants, a verdict in the chat.

The enumeration still happens, it is just short. Ask what goes wrong, find two or
three payers, and if the honest answer is "nobody pays much either way", say that
and skip the panel. A panel on a decision that does not matter is the cheapest way
to make this pass look expensive.

A decision that routes to `deep` instead — irreversible, or money, auth or security —
needs a corpus and invariants like any other artefact, and there is no worked example of
one here. Derive it from the same rule, and expect the failure modes to be consequences
rather than lines you can quote.
