Status: resolved
Assignee: Abdul (wayfinder session 2026-10-30)
Type: research

# What version 1 cost, and where its time went

## Question

What did version 1 cost for each feature it shipped, and where did its time go? Use the records that each run-issues and parallel-hunt finale wrote, which run-compare reads, and the git history where they fall short. Pick the unit the records support best, such as hours, tokens or money per shipped issue, and say why. Give the figure for all of version 1 and for Orderflow on its own, and break the time down by the stages the records carry, for example implementing, the gates and waiting on usage limits. "How the README tells the version story" puts the figure in the README's first-screen table, and its sentence "Then I measured where the time went and cut most of it" stays only if this ticket finds the breakdown.

## Answer

Version 1 spent 69.4 minutes of run time on each shipped issue: 846.9 hours across 84 measured runs for 732 shipped issues, from 30 August to 28 October 2026. Orderflow alone, in the map's window of 9 September to 24 October, spent 68.7 minutes: 652.7 hours across 67 runs for 570 issues. The median run is cheaper, 63.0 and 61.7 minutes, because a few long runs pull the mean up. With the bug hunts added, version 1 comes to 76.5 minutes and Orderflow to 75.1.

The unit is run hours per shipped issue: the wall clock of each run's main session, first transcript line to last, divided by the issues whose commit reached main. Every line a finale wrote carries hours. They moved by a factor of 1.9 across Orderflow's periods, while the API-equivalent price moved by 8.6 because the main model changed three times. And version 2 can read them the same way from its own session transcripts, without the version 1 scripts. Weighted tokens cannot be added across models, and the records hold no money; on Abdul's subscription none of it was a bill. Priced at list for comparison, the subagents in Orderflow's window came to $20 to $23 per shipped issue.

Inside Orderflow's runs a subagent was working for 76% of the wall clock and nothing ran for 20%. Of the agent hours, implementing took 54.5%, the review gate 21.7%, the verify gate 17.9% and the finale 3.9%, so the two gates together took 40%. The README sentence "Then I measured where the time went and cut most of it" stands for the time inside the runs. If "it" means the time, the cut waits for the version 2 figure.

The records cannot give the rest, and the gap is large. In Orderflow's window, 1,334 of the 2,528 commits on main (53%) landed while no run session was open: hunts, hardening, rulings, merges, prototypes and Abdul's own sessions. No record says how long that work took, so 69 minutes is the cost of the build loop, not of the whole pipeline. No field holds a wait on a usage limit either: a wait inside a session falls into the 20%, and nothing records a wait between sessions. Suite time inside a spawn, the stages of four of the five hunts, procurement's runs before 30 August and Orderflow's output tokens from 23 September to 22 October are missing too. A script over the 10 GB of session transcripts could recover most of it in a few hours of one session. Claude Code's documented default deletes transcripts after 30 days, although 66 older ones are still on disk.

The map's counts hold, but neither counts features. Of the 728 issue files, runs shipped 578, the direct road 25 and other routes 19; the other 106 were parked, closed or waiting for hardening.

Findings: `.scratch/workflow-v2/research/17-version-1-cost.md`.
