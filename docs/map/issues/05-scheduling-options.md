Status: resolved
Type: research

# How Claude Code can run a scheduled session

## Question

What ways exist today to start a Claude Code session on a schedule (every two weeks, or monthly) and get the result to Abdul? Cover cloud routines (/schedule), the desktop app's scheduled tasks and local cron with the CLI. For each, find the cost, whether the session can be interactive, where the output can land (email, a file, a claude.ai page) and whether the laptop has to be awake. Cite the current official docs.

## Answer

A cloud routine (/schedule) is the simplest fit. It runs with the laptop shut, uses the normal subscription, takes a custom cron such as `0 9 1 * *` for monthly, and leaves a full session Abdul can open and carry on from claude.ai/code/routines. Strict every-14-days cannot be written in cron; `0 9 1,15 * *` is the nearest. It starts from a fresh GitHub clone, so it cannot read local files. Desktop scheduled tasks need the laptop awake and skip runs missed during sleep. Local cron with `claude -p` is one-shot and needs a long-lived token.

Still to test once: whether the routine cron field accepts `1,15`, and whether a finished run emails or notifies Abdul.

Findings: `.scratch/workflow-v2/research/05-scheduling-options.md` on branch `research/scheduling-options`.
