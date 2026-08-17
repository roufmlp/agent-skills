# Picking the live ledger

Read this on every `/run-issues resume`, and on every revival from a halt,
before opening any `run.md`. `SKILL.md` holds the trigger; the procedure is
here, so a run that never resumes never pays for it.

The text below stood in `SKILL.md` until 2026-08-16 and moved here.

**Find the right ledger before reading any of it.** One script decides it. The
rules it applies, and the incidents behind each one, are in its own docstring:

```bash
python3 ~/.claude/skills/run-issues/find_live_ledger.py [--issues 348,345]
```

It prints one ledger path and exits 0, or exits non-zero having printed every
copy it examined and why each was refused. **A non-zero exit is a launch-time
stop:** report what it printed in the launch message and spawn nothing — a stop
before anything is spawned is not a mid-run stall. Pass `--issues` only to split
two live ledgers by scope.

The one way to get this wrong is to overrule the script by picking the freshest
file. On one measured run the freshest ledger belonged to an already-merged run,
and chasing it cost 25 minutes.

Only then: read that ledger, then `run-journal.md` once, then re-run pre-flight
before spawning anything, and recreate the cron.
