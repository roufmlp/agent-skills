# Installing the hooks

Copying a hook does nothing. Claude Code runs a hook only when an entry in
`settings.json` points at it, and a skill pack cannot write that entry for you.
So the install is two steps, and the second one is the step that matters.

## 1. Copy the files

```
mkdir -p ~/.claude/hooks
cp hooks/run-issues-foreground-gate.py hooks/run-issues-evidence-gate.py \
   hooks/coderules-gate.py hooks/retired-phrases-gate.py \
   hooks/origin-row-guard.py hooks/git-shared-state-guard.py \
   hooks/run-issues-brief-cap.py hooks/run-issues-typecheck-gate.py \
   hooks/machine-wide-kill-guard.py hooks/gate-commit-guard.py \
   hooks/rulings-write-guard.py hooks/run-issues-suite-gate.py \
   hooks/run-issues-wakeup-gate.py \
   ~/.claude/hooks/
```

Anywhere on disk works. Whatever you pick goes in the block below as an absolute
path, because the command runs in a shell whose working directory you do not
control.

## 2. Register them

Merge this into `~/.claude/settings.json` and replace `/ABSOLUTE/PATH/TO` with
where you put the files. If you already have a `hooks` key, add these objects to
its `PreToolUse` array rather than replacing the array.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Agent|Task",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/run-issues-foreground-gate.py"
          },
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/run-issues-evidence-gate.py"
          },
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/run-issues-brief-cap.py"
          },
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/run-issues-typecheck-gate.py"
          },
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/run-issues-wakeup-gate.py"
          }
        ]
      },
      {
        "matcher": "Edit|Write|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/coderules-gate.py"
          }
        ]
      },
      {
        "matcher": "Edit|Write|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/retired-phrases-gate.py"
          }
        ]
      },
      {
        "matcher": "Edit|Write|NotebookEdit|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/origin-row-guard.py"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/git-shared-state-guard.py"
          },
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/machine-wide-kill-guard.py"
          },
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/gate-commit-guard.py"
          },
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/run-issues-suite-gate.py"
          }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /ABSOLUTE/PATH/TO/rulings-write-guard.py"
          }
        ]
      }
    ]
  }
}
```

All twelve are `PreToolUse` hooks, so each runs before the tool call it matches
and can stop it. Exit 2 blocks that one call and feeds the hook's stderr back to
the model, which then fixes the call and reissues it. Exit 0 lets the call
through. None of them needs a timeout: each reads one JSON payload from stdin
and returns.

Put the block in `~/.claude/settings.json` to cover every project, or in a
repository's `.claude/settings.json` to cover one.

## run-issues-brief-cap.py, on `Agent|Task`

It matches one `subagent_type`, `run-issues-implementer`, and refuses one shape:
a FIRST-ATTEMPT brief longer than 400 words. Every other spawn on the machine
passes untouched at any length, and so does every retry (an `attempt N` marker
with N above 1), every correction round, and the escalated third implementer,
which is a different type name.

**What it assumes about your run, and what happens if that is not true.** The cap
is affordable only because the facts a brief used to restate live somewhere the
implementer already reads — this pack puts them in the run ledger's header, and
`agents/run-issues-implementer.md` tells the implementer to read that header
first. Install this hook without that arrangement and it will refuse briefs that
genuinely needed their length. Raise `CAP_WORDS` in the file, or leave the hook
out, rather than shortening a brief that carries something the implementer cannot
get anywhere else.

It writes one JSON line per implementer spawn it sees, exempt ones included, to a
file in the machine's temporary directory. `skills/run-issues/report_brief_cap.py`
is the only reader of that file, and the finale runs it. Nothing else is written
anywhere.

## run-issues-typecheck-gate.py, on `Agent|Task`

It matches three `subagent_type` names — the verify gate and both review gates —
and refuses one shape: a gate spawn whose tree exits non-zero on the project's
own `typecheck` script. The refusal names the first failing file and line.

**It costs nothing for anyone it does not match**: no git call, no typecheck, no
disk. It acts only when the spawn's working directory is inside a tree a live run
owns, which it resolves through `skills/run-issues/find_live_ledger.py` — so that
file must be present at `../skills/run-issues/` relative to the hook, or the hook
fails open and says so on stderr.

A tree whose `package.json` declares no `typecheck` script passes. So does a tree
whose typecheck cannot be run, a hunt's gates, and every payload it cannot read.
It caches a pass against the tree's git fingerprint in the machine's temporary
directory, so an unchanged tree is typechecked once per run, not once per gate.

## run-issues-foreground-gate.py, on `Agent|Task`

It judges a spawn whose `subagent_type` starts with `run-issues-` and refuses
two shapes: a `run-issues-verify-gate` spawn whose `run_in_background` is not
exactly `true`, and any other `run-issues-*` spawn whose value is not exactly
`false`. Every other spawn passes untouched, so `parallel-hunt` and ordinary
sessions never meet it.

The verify gate is the exception because it is the one worker the runner has
something to do beside: the review gate. A verify gate in the background and a
review gate in the foreground on the next turn overlap by construction. Before
2026-09-04 the hook required `false` everywhere and left "both gates in one
message" as the only concurrent shape; one fifteen-issue run never once produced
it, at a measured cost of 97 minutes.

Skip it and `skills/run-issues/SKILL.md` still orders the runner to name the
field, but that order is a reminder, and one run mixed the values anyway. What
you lose is not clock. A re-measure of that run found background spawns cost it
nothing measurable, because task notifications woke the runner within seconds of
every completion. What you lose is the guarantee: without the gate the run bets
on notification delivery holding, and that is harness behaviour rather than a
promise.

It cannot catch a turn that ends without spawning at all. Nothing at
`PreToolUse` can, because there is no call to inspect. Cover that class with a
resume cron.

## run-issues-evidence-gate.py, on `Agent|Task`

It refuses a verify-gate or review-gate spawn unless the issue file named in the
prompt already holds an implementation record, and unless that record is newer
than the last verdict of the kind now being spawned. Implementer spawns and every
other agent type pass untouched.

**It needs one file from this pack: `skills/lib/check_verdict.py`.** The hook
imports that module's heading matcher rather than growing a second one, because
issue files write the record heading five different ways and one matcher already
handles all of them. It looks in `~/.claude/skills/lib` by default; set
`RUN_ISSUES_LIB` if you keep the pack elsewhere. If the import fails the hook
refuses every gate spawn rather than passing them, on the grounds that a guard
which switches itself off silently is worse than no guard.

Skip it and a gate can be spawned over an issue file nobody has implemented. It
will produce a verdict, and that verdict will pass `check_verdict.py`, because
that script grades a verdict's shape and this fault is upstream of it. What you
lose is the guarantee that a gate had something to judge.

## coderules-gate.py, on `Edit|Write|NotebookEdit`

It blocks the first edit of a code file in each context and tells the model to
read your code rules before reissuing. One refusal per context, then silence. A
subagent counts as a context of its own, because it starts fresh and never saw
its parent read anything. Markdown, `.scratch`, `node_modules` and `.git` pass.

Point it at your own rules with the `CODERULES_PATH` environment variable. The
default is `~/.claude/coderules.md`. This pack publishes mine as
`steering/coderules.md`, meant to be replaced rather than adopted, and two
sentences in the refusal message name the two rules of mine that get skipped
most. Edit them to name two of yours.

Skip it and the rules load only when a session remembers to invoke the skill.
Remembering is the failure the hook exists for; that is the whole of what you
lose.

## retired-phrases-gate.py, on `Edit|Write|NotebookEdit`

It refuses a write that puts a superseded sentence into a steering file, and it
names what replaced it rather than only what is wrong.

The problem it solves is drift between files that all tell an agent what to do.
A rule gets re-ruled in one place, another file keeps the old wording, and the
old wording wins locally, because the agent reading it cannot know a newer
ruling exists. One sweep of a real tree found eighteen of those, all repaired by
hand, with nothing to stop the nineteenth.

The denylist is `skills/lib/retired_phrases.py`, and it is the only copy — the
hook and `skills/lib/test_retired_phrases.py` both read it. **Its five entries
are the author's own retired wording, kept as worked examples. Replace them with
yours or the hook polices nothing.** Point it elsewhere with the
`RETIRED_PHRASES_LIB` environment variable.

Scope is four path classes under `~/.claude`: `CLAUDE.md`, `questionrules.md`,
`skills/<name>/SKILL.md` and `agents/<name>.md`. It deliberately lets past every
`decisions.md`, every project file, a repository's own `CLAUDE.md`, and every
Bash command. The `decisions.md` exemption is load-bearing: a provenance file
quotes dead wording on purpose, and a guard that fought that would be switched
off within a week.

Skip it and you keep the reporting test, which finds the same drift after it has
already reached the file.

## origin-row-guard.py, on `Edit|Write|NotebookEdit|Bash`

It refuses a register row written into a `register.d/` shard directory that does
not name where the fault came from — either a register table declaring no
`origin` column, or a row under one whose origin cell is blank. It judges only a
table whose header carries both `audience` and `severity`, which is the register
row shape and not the prose tables a shard also holds. Every path outside a
shard directory passes untouched.

**It judges the addition, not the file.** An Edit and a heredoc append a row
alone, so the guard reads the file on disk above them to find the table header —
but a bad row ALREADY on disk is somebody else's, and refusing the next writer
for it blocks the very append that would repair it. So a row fault above the
lines being written is let past. The header check is not filtered, because a
table that declares no `origin` column cannot carry the key on the new row
either, whoever typed the header.

**It needs one file from this pack: `skills/run-issues/check_origin.py`.** The
hook reuses that script's row reader rather than growing a second one. It looks
in `~/.claude/skills/run-issues` by default; set `ORIGIN_CHECK` if you keep the
pack elsewhere. If the import fails the hook PASSES, which is the opposite of
the evidence gate's choice above and is deliberate: this rule has a second
enforcer downstream in `check_origin.py` itself, which promotion runs before it
resolves a row, so a silent pass here is caught rather than lost.

**Its Bash road does not work in this pack, and that is stated rather than
discovered.** Resolving a redirect target needs `generated-file-guard.py`'s
parser, and `MANIFEST.md` withholds that file. Without it a heredoc appending a
row to a shard passes here. Edit and Write are judged in full. The two Bash
classes in `test_origin_row_guard.py` skip themselves when the parser is absent,
so the test reports the gap instead of failing on it; drop that sibling in
beside the guard and both start working with no change to either file.

Skip the hook and a new register table can be typed without the column at all,
which is the one shape `check_origin.py` cannot report: it skips a table
declaring no `origin` column on purpose, because a register holds historical
rounds under a dozen header shapes and grading all of them would report hundreds
of faults nobody can act on. A hook sees only writes happening now, so it can
demand the column without ever meeting history. That is the whole of what you
lose.

## rulings-write-guard.py, on `Edit|Write`

It refuses a write that would leave a `.scratch/rulings.md` holding more entries
`skills/lib/rulings.py` cannot read than it holds now, and a write that empties
one that currently holds entries. It applies the edit in memory, parses the
result with that one reader, and compares the two counts. It writes nothing.

A ruling the reader cannot parse is dropped in silence, and
`skills/lib/check_queue_shard.py` grades a queued question against these entries
alone, so a dropped ruling cannot refuse the question it answered and the next
pass asks it again. Nine of 106 entries failed that way on one project on
2026-09-20, four of them written the day before, so the rate is live rather than
historical.

A write leaving the same number of bad entries or fewer passes, because a pass
repairing an inherited mess has to be able to land a partial repair. So does a
`rulings.md` outside a `.scratch` tree, every Bash command, a payload it cannot
parse, a missing reader, and an `Edit` whose `old_string` does not appear exactly
once, which fails on the Edit tool's own terms.

## git-shared-state-guard.py, on `Bash`

It refuses the git commands that reach across sessions sharing one checkout. A
git worktree gets its own index; the MAIN checkout has exactly one, and every
session working there shares it. So a wide `git add` there stages whatever every
other session has touched, and the commit that follows carries work its message
does not describe.

In the main checkout it refuses a wide `git add`, a `git commit` that names no
paths, and the destructive whole-tree commands. A merge in progress is the one
exception, because git will not let a merge commit name its paths: a pathless
`git commit` or `git merge --continue` that concludes it passes when every staged
path is one the merge brings, and prints the list of paths it carries. A staged
path the merge does not bring is refused by name. In a linked worktree it refuses
one thing, a bare `git stash` and a `git stash pop`, because the stash stack is
the single piece of git state a worktree does not get its own copy of. Every
other git command passes, every non-Bash call passes, and it writes nothing.

**Install it only if you run several agents against one checkout.** On a machine
where one session holds the repository it refuses correct commands all day, and
the honest answer there is to leave it out. It applies no worktree-count test of
its own on purpose: a day with no worktree present does not prove the session is
alone, and a guard that goes quiet on that evidence is worse than no guard.

It holds no exception list. A wide but honest commit uses
`--pathspec-from-file`, so one rule covers every commit: the commit names what
it carries.

Skip it and you keep the habit, and a habit does not survive the case that
motivated the guard — a session that staged its two files BY NAME still lost
them, because another session committed between its `git add` and its
`git commit`.

## gate-commit-guard.py, on `Bash`

It refuses a `git commit` by one of the six adversarial gate roles — the verify
gate, both review gates, and the hunt's claim and two fix gates. The runner
commits; a gate reports. The `git -c core.hooksPath=... commit` spelling is
caught too, because a flag between `git` and `commit` is still a commit and that
spelling is the one that turns the other hooks off.

Every other role passes at any command, including the runner and the main
session, which is where commits are supposed to come from. `git add`, `git stash`
and every read pass for a gate as well: staging has not changed history, and the
commit is where this bites. It reads the command string and the spawning agent's
type, and it writes nothing.

It says nothing about a gate's FILE writes. That is a separate rule with a
separate control, and `MANIFEST.md` withholds the hook that enforces it, so in
this pack it is a rule the loop holds rather than one you have.

**Install it only if you spawn gates as subagents with these type names.** It
keys on `agent_type`, so a loop that grades diffs some other way never meets it,
and a loop that names its gates differently needs those names added to `GATES` in
the file. A name in that list that no `agents/` file defines is a typo, and
`test_gate_commit_guard.py` pins the list against the pack's own role files.

Skip it and the rule survives only in prose — in `skills/run-issues/SKILL.md` and
in `skills/run-issues/check_permission_floor.py`, which already says in as many
words that a gate which commits is a finding rather than a permission to grant.
Both said it before the run that broke it twice, by an agent that had read its
own brief. That is the whole of what you lose: two written rules instead of a
refusal.

## machine-wide-kill-guard.py, on `Bash`

It refuses a kill that selects processes by PATTERN rather than by pid: `pkill`
and `killall` in any spelling, and `kill` fed from a substitution that selects by
pattern, such as `kill $(pgrep -f vitest)` and its backtick form. Those three are
the roads to killing a process you did not start.

`kill <pid>` with a literal number is never refused, nor is a pid read back from
a file the caller wrote, nor `pgrep` on its own, which is a read. The refusal
prints the capture-the-pid road rather than only the rule. It reads the command
string and nothing else — no file, no tree, no ledger — and it writes nothing.

It has no opinion about who typed the command, and that is deliberate. A
machine-wide kill is wrong from a gate, from an implementer and from the runner
alike, because every one of them shares the machine with the others.

**Install it only if more than one agent can be running on your machine at once.**
Alone at a keyboard, `pkill -f node` is a reasonable thing to type and this hook
will refuse it all day. What it is for is the shape that motivated it: two gates
running their own suites in their own trees, one of them proving what a SIGKILL
leaves behind, and `pkill -9 -f vitest` reaching the other one's processes. The
gate disclosed the call in its own verdict, which is the only reason anybody
knew; nothing refused it and nothing recorded which processes died.

Skip it and the rule survives only as a line in a brief. The run that met this
had that line already — "kill only what you started" was implicit in every gate
brief on the day it was broken. That is the whole of what you lose: a reminder
instead of a refusal.

## run-issues-suite-gate.py, on `Bash`

It refuses a whole test suite in a run unless it goes through the wrapper,
`skills/run-issues/run_suite.py`, at a stage the caller owns. A whole suite is
`npm test` and its cousins under `pnpm`, `yarn` or `bun`, or `vitest` with no
argument naming a file or a directory. An implementer's stage is `issue` and the
verify gate's is `verify`. The runner, which is the main session inside a live
run's tree, gets `baseline` and `correction`, and `finale` once the run ledger's
`State:` line names a finale stage. A light issue's implementer gets no whole
suite at all, and the refusal points it at `skills/run-issues/scoped_suite.py`.

A run that names a file or a directory passes. So do the review gates, every
other agent, and the main session outside a live run's tree, which is where you
run a suite by hand. Only a command that launches a suite is judged, so
`npm ls vitest` and `grep vitest package.json` never meet it. It writes nothing.

**It needs four files from this pack**: `find_live_ledger.py`,
`check_finale_stage.py` and `issue_level.py` in `skills/run-issues/`, and
`skills/lib/set_level.py`, which the first and third import. The hook looks for
them at `../skills/run-issues/` relative to itself, which is
`~/.claude/skills/run-issues` once installed as above; set `RUN_ISSUES_SKILL_DIR`
if you keep the pack elsewhere. Where it cannot read the live ledgers, the main
session's suite passes. Where it cannot read an issue's level, the issue is
judged full. Both say so on stderr.

**Install it only if your project's suite is slow enough to matter and your run
ledger names the command.** The refusals print the wrapper call with the ledger
header's `Full suite:` command in it, so a loop without that header gets a road
it cannot follow.

Skip it and the wrapper is a habit. Four runs on one project spent 665 minutes
on 206 whole suites, and 62 of the 128 an implementer ran re-read a tree nothing
had changed. `run_suite.py` refuses that repeat only when a suite goes through
it, and without this hook nothing makes a suite go through it. That is what you
lose: the only road to a whole suite becomes one road among several.

## run-issues-wakeup-gate.py, on `Agent|Task`

It refuses a `run-issues-*` spawn from inside a live run's tree until that run's
ledger carries a header line `Wakeup cron: <job id> pid <process id>` naming the
`claude` process that asks. `skills/run-issues/wakeup_cron.py record` writes that
line after the runner makes the cron with `CronCreate`. A cron job lives in the
memory of the process that made it, so a resume in a new process is refused until
it makes a new job. The refusal prints the three steps: look in `CronList`, make
the job from what `wakeup_cron.py args` prints, and record it in every copy of the
ledger.

Every other spawn passes before the hook reads anything, and so does a run spawn
outside a live run's tree. A hook environment with no `CLAUDE_PID` passes any line
that names a job. It cannot catch a line written by hand for a job never made. It
writes nothing.

**It needs six files from this pack**: `find_live_ledger.py`, `wakeup_cron.py`,
`check_finale_stage.py`, `check_issue_ready.py` in `skills/run-issues/`, and
`skills/lib/set_level.py` with `skills/lib/next_batch.py`, which
`find_live_ledger.py` imports. The hook looks for them at `../skills/run-issues/`
relative to itself, which is `~/.claude/skills/run-issues` once installed as
above. Where it cannot read them, or the live ledgers, the spawn passes and the
hook says so on stderr.

Skip it and the wakeup cron is a step in `SKILL.md` that a runner can forget. The
author saw runs forget it, and a run that stops with no cron stays stopped until
somebody looks.

## Check it worked

`run-issues-evidence-gate.py` ships its test, `test_run_issues_evidence_gate.py`.
Run it from this directory:

```
RUN_ISSUES_LIB=../skills/lib python3 test_run_issues_evidence_gate.py
```

`retired-phrases-gate.py` ships its test too, `test_retired_phrases_gate.py`,
which runs from this directory with no environment set. So does
`origin-row-guard.py`, as `test_origin_row_guard.py`; it needs no environment
either, and it reports five skips, which is the Bash gap named above and not a
failure. `run-issues-foreground-gate.py` ships
`test_run_issues_foreground_gate.py`, 27 behavioural cases with no environment
set. `git-shared-state-guard.py` ships `test_git_shared_state_guard.py`, 79
cases; it builds a real git repository with a linked worktree in a temporary
directory, so it needs `git` on the path and takes a few seconds.
`machine-wide-kill-guard.py` ships `test_machine_wide_kill_guard.py`, 19 cases on
command strings alone, with no environment set and nothing on disk.
`gate-commit-guard.py` ships `test_gate_commit_guard.py`, 21 cases; one of them
reads `../agents/` to pin the role list, and skips itself when the hook has been
copied out of the pack on its own.
`run-issues-typecheck-gate.py` ships `test_run_issues_typecheck_gate.py`, 31
cases; its fixture trees are built in a temporary directory, so it needs no
environment either.
`rulings-write-guard.py` ships `test_rulings_write_guard.py`, 14 cases; it drives
the hook beside it as the harness does, a JSON payload on stdin and an exit code
out, and it needs `skills/lib/rulings.py` reachable at
`~/.claude/skills/lib/rulings.py`, which is where the hook itself looks for the
reader.
`run-issues-suite-gate.py` ships `test_run_issues_suite_gate.py`, 56 cases; its
ledgers and git repositories are built in a temporary directory, and it reads
the four sibling files above at `../skills/` and the three role files it pins at
`../agents/`, so run it from this directory inside the pack. One case, the
registration check, skips itself when no `settings.json` sits beside the hooks
directory, which is every copy of the pack that has not been installed.
`run-issues-wakeup-gate.py` ships `test_run_issues_wakeup_gate.py`, 25 cases; its
ledgers and git repositories are built in a temporary directory, and it imports
the skill files above from `../skills/`, so run it from this directory inside the
pack. Its registration check skips the same way.

Only `coderules-gate.py` ships no test, because it has none in the tree it came
from. It carries a drill in its docstring instead: pipe a JSON payload on stdin
and read the exit code.

That drill proves the script. It says nothing about the registration, which is
the half that fails silently. For that, start a session and make an edit or a
spawn the hook should refuse. If nothing is refused, step 2 did not take.

## Hooks the skills name and this pack does not carry

Read `skills/` and you will meet other hook names — `machine-preflight.py`,
`model-map-gate.py`, `model-landed-check.py`, `number-claim-guard.py`,
`run-state-path-guard.py`, `generated-file-guard.py`, `gate-source-write-guard.py`,
`gate-issue-write-guard.py`, `run-issues-risk-path-guard.py`,
`run-issues-parallel-gates.py`, `run-issues-criteria-fault.py`. **None of them is in
this directory.** Where a skill says one of those refuses something, read it as a
rule the loop holds and not as a control you have: `MANIFEST.md` says why each is
withheld and which of them a later sync should publish.

Nothing here calls them, so nothing breaks. What you lose is the refusal. A rule an
agent is asked to remember is weaker than a rule that answers a tool call, and the
gap is worth knowing about before you rely on one of those sentences. Every one of
these is a `PreToolUse` or `SubagentStop` hook of about a hundred lines, so the road
open to you is to write your own against the rule the skill states, with the shape
the published hooks beside it carry: payload on stdin, reason on stderr, exit 2 to refuse,
exit 0 on anything it cannot read.

`generated-file-guard.py` is the one of those eleven that a published hook actually
reaches for: `origin-row-guard.py` loads its `bash_targets` parser to resolve a
redirect target, and passes every Bash write when it is absent.
