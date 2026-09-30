# Picking the live ledger

Read this on every `/run-issues resume`, and on every revival from a halt,
before opening any `run.md`. `SKILL.md` holds the trigger; the procedure is
here, so a run that never resumes never pays for it.

The text below stood in `SKILL.md` until 2026-08-16 and moved here.

**Find the right ledger before reading any of it.** One script decides it. The
rules it applies, and the incidents behind each one, are in its own docstring:

```bash
python3 ~/.claude/skills/run-issues/find_live_ledger.py
```

**It keys on the current directory** (ticket 38, the one-run-per-feature layout
ticket, ruling 11). Run it from inside
the run's own worktree: it prints the one ledger whose `Worktree:` line names that
tree and exits 0. Run from the main checkout, or from a tree no live run names,
it lists every live run by batch id on stderr and exits 1 — that listing is the
answer, and the human picks by changing directory, never by count and never by
freshness. **A non-zero exit is a launch-time stop:**
report what it printed in the launch message and spawn nothing — a stop before
anything is spawned is not a mid-run stall. `--list` prints every live run, tab
separated, for a reader that wants all of them; `--overlap <ids>` is the
pre-flight's range check.

The one way to get this wrong is to overrule the script by picking the freshest
file. On one measured run the freshest ledger belonged to an already-merged run,
and chasing it cost 25 minutes.

Only then: read that ledger, then `run-journal.md` once, then re-run pre-flight
before spawning anything, and recreate the cron.

**Recreate it, never double it.** Run `CronList` first. A job whose prompt names
this batch is still alive, because this is the process that made it: keep it,
and run `wakeup_cron.py record` with its id if the ledger's `Wakeup cron:` line
names another. Otherwise make one exactly as "Resume across usage limits" in
`SKILL.md` says. A job dies with the process that made it, so a resume in a new
session always makes one, and `~/.claude/hooks/run-issues-wakeup-gate.py` refuses
the first spawn until it has.
