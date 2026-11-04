Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: research

# What Claude Code offers to measure and cap a session's context

## Question

Abdul finds that an agent past 300k to 400k tokens of context makes mistakes on serious work, and wants no version 2 session or agent to go past 300k. His `CLAUDE.md` already has context hygiene rules, but they only ask the agent to behave, and by his own rule a reminder does not work.

Find the facts a refusal would need, from the Claude Code docs and the transcript format on this machine:

- Can a hook read the current context size of the session it runs in? Which hook events carry `transcript_path`, and does the transcript's `usage` (input, cache creation and cache read tokens) give the context size of the last turn?
- Do the same hooks fire for subagents and for agents a saved workflow starts, and can they read the agent's own context size, not the parent's?
- What can a hook do once the size passes a limit: block tool calls, block the next prompt, or ask for compaction? Can it leave one write open, so the agent can save a handoff first?
- Does a setting such as `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` compact at a set share of the window, and what is the window for each model Abdul uses (Opus, Sonnet, with and without the 1M window)?
- How large did version 1's agents get? Orderflow's run records and session transcripts show the largest contexts per role.

Write the findings with a source for each, and say which facts could not be found.

## Answer

A hook can measure a session's context and stop it, and a setting can compact it earlier; nothing does both. The facts, each with its source, are in [the context-size research](../research/34-context-size-facts.md).

**Measuring.** No hook event carries the size ready to use, except two that are no help for a cap (`PreModelSwitch`, and `SessionStart` on a resume). Every event carries `transcript_path`, and the input, cache-creation and cache-read tokens on the last assistant line add up to the context size. Over 282 compactions on this machine that sum came within a median 1,720 tokens of the size Claude Code itself recorded. The file can lag by one turn, and transcripts reach 48 MB, so a hook reads from the end of the file.

**Subagents.** The docs say settings and plugin hooks fire inside subagents, `PreToolUse` included, with the subagent's `agent_id`. Its own transcript sits at `<session>/subagents/agent-<agent_id>.jsonl`, so a hook can read the subagent's size rather than the parent's. That path is seen on this machine, not stated in the docs, and the docs do not say that hooks fire for agents a saved workflow starts. Subagents begin at about 85k to 95k tokens before they read anything.

**Stopping.** A `PreToolUse` deny blocks a tool call, and it can let one call through, such as a write to the handoff file. A `UserPromptSubmit` block stops a prompt, and `continue: false` stops Claude. No hook can ask for compaction.

**Compacting earlier.** Opus 5.5, Opus 5 and Sonnet 5.5 all have a 1M window. `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (100k to 1M) sets the window for every model and beats every other setting, the subagent frontmatter field included. `~/.claude/settings.json` sets a 400k window for Opus 5.5 alone, so Opus 5.5 compacts near 367k while Opus 5 and Sonnet 5.5 agents reached 934k and 776k. A window of about 333k would compact near 300k; that figure is fitted from one window value and not tested. Compaction summarises and carries on, so it does not stop an agent.

**Version 1's sizes.** Across 4,790 Orderflow transcripts, main sessions peaked at 966k with a 90th percentile of 415k; `/run-issues` main sessions had a 90th percentile of 705k. Implementers had a 90th percentile of 365k and a peak of 934k, and the finale 597k. 180 of 514 main sessions and 252 of 1,260 implementers went past 300k.
