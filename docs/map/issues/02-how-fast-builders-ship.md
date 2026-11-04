Status: resolved
Type: research

# How fast solo builders ship with Claude Code today

## Question

What do people who ship small apps quickly with Claude Code, or agents like it, actually do between idea and deploy? Use primary sources: Anthropic's own Claude Code docs and engineering posts (plan mode, spec-first builds, subagents, hooks) and first-hand write-ups by the builders. Report the steps they use, what they skip, how they check the result, and any measured times. Say where each approach would and would not suit a product holding real customer data.

## Answer

Fast builders write a one-page spec, or have Claude interview them into a SPEC.md, then build in a fresh session one small feature at a time, each with a check the agent can run itself. They skip per-action approvals (auto mode), heavy context management and, often, reading the code. The checks are mechanical: tests, typecheck, a Stop hook, a browser pass end to end, and one fresh-context review against the spec. Anthropic's own C-compiler post warns that passing tests do not prove the work is complete, so the done-check has to be strong.

Measured times are thin. One solo builder reported 26 days and 97 active hours for one app; no primary source gives an idea-to-deploy time for an app holding customer data. Anthropic's auto-mode post reports a 17% miss rate on overeager actions and says it does not replace human review on high-stakes systems.

What it means for the fast lane: a spec plus a done-check the agent can run, mechanical evidence, one fresh review, capped unattended runs and one sign-off from Abdul. No customer data, money, auth or secrets in that lane.

Findings: `.scratch/workflow-v2/research/02-how-fast-builders-ship.md` on branch `research/how-fast-builders-ship`. The solo builder's name and some habits of Anthropic staff come from secondary sources and are marked unconfirmed there.
