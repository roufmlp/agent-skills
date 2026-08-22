# Installing the hooks

Copying a hook does nothing. Claude Code runs a hook only when an entry in
`settings.json` points at it, and a skill pack cannot write that entry for you.
So the install is two steps, and the second one is the step that matters.

## 1. Copy the files

```
mkdir -p ~/.claude/hooks
cp hooks/run-issues-foreground-gate.py hooks/coderules-gate.py ~/.claude/hooks/
```

Anywhere on disk works. Whatever you pick goes in the block below as an absolute
path, because the command runs in a shell whose working directory you do not
control.

## 2. Register them

Merge this into `~/.claude/settings.json` and replace `/ABSOLUTE/PATH/TO` with
where you put the files. If you already have a `hooks` key, add these two objects
to its `PreToolUse` array rather than replacing the array.

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
      }
    ]
  }
}
```

Both are `PreToolUse` hooks, so both run before the tool call they match and can
stop it. Exit 2 blocks that one call and feeds the hook's stderr back to the
model, which then fixes the call and reissues it. Exit 0 lets the call through.
Neither hook needs a timeout: both read one JSON payload from stdin and return.

Put the block in `~/.claude/settings.json` to cover every project, or in a
repository's `.claude/settings.json` to cover one.

## run-issues-foreground-gate.py, on `Agent|Task`

It refuses a spawn whose `subagent_type` starts with `run-issues-` unless
`run_in_background` is exactly `false`. Every other spawn passes untouched, so
`parallel-hunt` and ordinary sessions never meet it.

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

## Check it worked

Neither hook ships a test, because neither has one in the tree it came from.
Each carries a drill in its docstring instead: pipe a JSON payload on stdin and
read the exit code. The four payloads at the top of
`run-issues-foreground-gate.py` take a second to run and cover both directions,
two that must refuse and two that must pass.

That drill proves the script. It says nothing about the registration, which is
the half that fails silently. For that, start a session and make an edit or a
spawn the hook should refuse. If nothing is refused, step 2 did not take.
