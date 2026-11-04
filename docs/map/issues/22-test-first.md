Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: grilling
Blocked by: 08, 19, 21

# Whether the build agents work test-first

## Question

Version 1's implementer worked test-first. Its agent file, `~/.claude/skills/workflow/agents/run-issues-implementer.md`, tells it to invoke `/tdd` and work at the seams agreed in the issue file. Version 2 makes `tdd` a toolbox skill that a session picks up when it needs one, as "What the careful lane keeps" set out, and no ticket says whether any build agent must use it: the implementer in `/build-feature`, the one-note `/goal` session or the fast lane's build session.

One rule comes close. Before a run starts, a verifier refuses any done check that already passes, as "How a feature with several change notes runs without Abdul" ruled, so each note's checks fail before the work begins. That covers the note as a whole, not the steps inside it.

Decide whether test-first is a lane step, a line in the implementer's agent file or the agent's own choice, and which lanes it covers. The fast lane's three-day limit may argue against it there. Decide too what refuses work that skips it, because a line in a brief is a reminder and reminders fail. In version 1 the seams `/tdd` asks for were agreed in issue files, which retire; say where they come from now, whether the change note, the core design or the agent.

The lighter option is one line in the implementer's agent file that loads `/tdd`, with nothing to enforce it. An answer heavier than that says what the lighter one would cost.

## Answer

Test-first is required in the careful lane, and a check refuses work whose tests prove nothing. The check does not look at the order of the work. It runs each new test against the code from before the note, and each one must fail. Version 1 is the reason. About 27 to 33% of the 196 gate rejects found in Orderflow's verdict files were about tests, although the implementer was told to work test-first. In most of them a test was missing, or a test stayed green when the code was wrong. No verdict found a test written after its code, and git could not have shown one, because the version 1 implementer never committed. The weak test was the fault, not the order.

**Who it covers.** The `/build-feature` implementer, the one-note `/goal` session and the parallel-hunt fixer. In the fast lane the build session chooses: `tdd` stays in the toolbox, with no rule and no check. An MVP holds nothing real and has three days.

**The instruction.** The implementer's and the fixer's agent files each tell the agent to work through `/tdd`. For a one-note change, the lane block in the product's `CLAUDE.md` says the same. These lines are not the control; the red check is.

**Seams.** They come from the modules part of the core design, so each seam already has an owner and import rules behind it. A new module needs Abdul's approval in the interview, as "How the careful lane keeps every slice aligned to the core design" ruled. A new seam inside an existing module is the one case he does not see first, so the agent records it in the report with the alternatives it rejected, and does not wait. Matt Pocock's `tdd` tells the agent to ask the user which seams to test, and nobody is there to answer, so each unattended caller's agent file carries the "do not wait for a seam" line. "How someone installs it" put that line in the fixer's file alone; `/build-feature` adds the implementer.

**The red check.** After the implementer finishes, the check puts back the source files from before the note, keeps the new test files and runs the tests whose names did not exist before. Each must fail. A test that passes on the old code passes by construction, or was written to match code that already worked, and the check refuses the note. A test that cannot load because its new module does not exist counts as a fail. Tests whose names did not change are ignored. A test that protects behaviour the note does not change starts with `keeps:`, the check skips it, and the report lists it for the reviewer. Only vitest tests are in scope. Running a new Playwright spec on the old code means building and starting the old app, an unmeasured one or two minutes a note; the screenshot baselines and the done checks give the screens some cover. The check costs seconds.

**Who runs it.** One function in the suite script that "How the careful lane keeps the test suite fast and trusted" put in the plugin. The implementer runs it before it hands over, so it finds its own weak tests while it can still fix them. The verifier's scoped run always runs it again, and that run is the refusal. For a one-note change, the note check hook calls the same function before the change merges to local main, so a session cannot skip it. That hook already refuses commits for screenshots and the core design, so no new tool arrives.

**Strikes.** A refusal at the verifier is a strike, like any verifier reject. Version 1 treated a weak proof of correct behaviour as a correction round, not a strike, and 76 of the 196 rejects were of that kind. Version 2 has no correction rounds, and the red check does not bring one back: the implementer runs the same function on the same tree first, so a refusal at the verifier means it skipped the check or ignored the result. This is a default.

**The parallel-hunt fixer.** No new check. The finder writes a pinning test that fails on the current code before the fixer starts, and the fix gate checks that it fails without the fix, so red before green is already proven for each fix.

**What was left out.** Mutation testing, which version 1's gates did by hand on private copies. A tool such as Stryker finds more weak tests than the red check, since it also catches a test too loose to notice a small bug in new code, but it runs for minutes a note, and version 1's two gates already took 40% of the agent hours. The audit's Bugs row shows when weak tests let bugs through, and a later change can add mutation testing for risk-class notes only.

**What the lighter option would cost.** One line in the agent file that loads `/tdd`, with nothing to enforce it, is a reminder. Version 1 had that line and still sent about a third of its rejects back for weak tests.

**Budget.** The red check counts against the plugin budget from "How a regular audit keeps the workflow small". This is a default.

The facts behind this answer are Orderflow's version 1 gate verdicts at `~/code/orderflow/.scratch/*/runs/*/verdicts/` (803 files read, 196 rejects, about 60 left unparsed), `~/.claude/skills/workflow/agents/run-issues-implementer.md` and the correction round rule in `run-issues/SKILL.md`.

`CONTEXT.md` now defines red check.

Changed by "What a run does when notes collide or fail" (2026-11-01): the note's migrations count as source, and every check run builds its test database from empty. The final fix round gets the red check against the commit the final check tested.

Changed by "Where the note check lives, and baselines for changed screens" (2026-11-01): the red check runs in the `pre-merge-commit` hook on every merge into main, for the whole feature against main's code from before it, so one-note changes are no longer a special case. Main merges with `--no-ff` so the hook always fires.
