# Installing the hooks

Copying a hook does nothing. Claude Code runs a hook only when an entry in
`settings.json` points at it, and a skill pack cannot write that entry for you.
So the install is two steps, and the second one is the step that matters.

## 1. Copy the files

```
mkdir -p ~/.claude/hooks
cp hooks/run-issues-foreground-gate.py hooks/run-issues-evidence-gate.py \
   hooks/coderules-gate.py hooks/retired-phrases-gate.py \
   hooks/origin-row-guard.py ~/.claude/hooks/
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
      }
    ]
  }
}
```

All five are `PreToolUse` hooks, so each runs before the tool call it matches
and can stop it. Exit 2 blocks that one call and feeds the hook's stderr back to
the model, which then fixes the call and reissues it. Exit 0 lets the call
through. None of them needs a timeout: each reads one JSON payload from stdin
and returns.

Put the block in `~/.claude/settings.json` to cover every project, or in a
repository's `.claude/settings.json` to cover one.

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
failure.

The other two ship no test, because neither has one in the tree it came from.
Each carries a drill in its docstring instead: pipe a JSON payload on stdin and
read the exit code. The four payloads at the top of
`run-issues-foreground-gate.py` take a second to run and cover both directions,
two that must refuse and two that must pass.

That drill proves the script. It says nothing about the registration, which is
the half that fails silently. For that, start a session and make an edit or a
spawn the hook should refuse. If nothing is refused, step 2 did not take.

## Hooks the skills name and this pack does not carry

Read `skills/` and you will meet other hook names — `machine-preflight.py`,
`model-map-gate.py`, `model-landed-check.py`, `number-claim-guard.py`,
`run-state-path-guard.py`, `generated-file-guard.py`, `gate-source-write-guard.py`,
`run-issues-parallel-gates.py`, `run-issues-criteria-fault.py`. **None of them is in
this directory.** Where a skill says one of those refuses something, read it as a
rule the loop holds and not as a control you have: `MANIFEST.md` says why each is
withheld and which of them a later sync should publish.

Nothing here calls them, so nothing breaks. What you lose is the refusal. A rule an
agent is asked to remember is weaker than a rule that answers a tool call, and the
gap is worth knowing about before you rely on one of those sentences. Every one of
these is a `PreToolUse` or `SubagentStop` hook of about a hundred lines, so the road
open to you is to write your own against the rule the skill states, with the shape
the five published hooks carry: payload on stdin, reason on stderr, exit 2 to refuse,
exit 0 on anything it cannot read.

`generated-file-guard.py` is the one of those nine that a published hook actually
reaches for: `origin-row-guard.py` loads its `bash_targets` parser to resolve a
redirect target, and passes every Bash write when it is absent.
