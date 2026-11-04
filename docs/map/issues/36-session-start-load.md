Status: resolved
Assignee: Abdul (wayfinder session 2026-11-02)
Type: research
Blocked by: 35

# What fills a session's first 100k tokens

## Question

"How every version 2 session stays under 300k tokens" set the compaction window at 400k for now, because every session starts at about 100k before it reads anything: a median of 105k for main sessions and 83k to 94k for subagents in version 1 (Explore 59k). The window drops to 300k once that start load falls.

Measure what makes up the start load, with a token count for each part: the system prompt, built-in tool definitions, each MCP server's tools (deferred and loaded), the skill list, the agent list, `CLAUDE.md` and its imports, memory, and hook output at session start. Do it for a main session on this laptop, for a subagent, for a workflow agent if one can be measured, and for a cloud routine session.

Then say which parts version 2 can cut or scope per lane (for example MCP servers a build session never uses, or skills a subagent never needs), what each cut saves, and what controls Claude Code offers to do it. Say which facts could not be found.

## Answer

A main session on this laptop starts at about 107k tokens and a subagent at 90k to 100k. Most of that is text Abdul's own setup adds, not Claude Code itself. The facts, each with its source and a label, are in [the start-load research](../research/36-session-start-load.md). The Claude CLI was logged out, so no live with-and-without run was possible: every part count below except one old `/context` table is worked out from exact character counts in the transcripts, and each carries that caveat.

**What a main session holds** (this session, 106,727 at the first response):

| Part | Tokens |
| :- | -: |
| Deferred MCP tool names (729) | about 38,000 |
| Skill listing (77 skills) | about 9,900 |
| System prompt | about 12,300 |
| `CLAUDE.md` and `MEMORY.md` | about 4,700 (about 11,400 in Orderflow) |
| MCP server instructions | about 2,600 (about 5,500 in Orderflow) |
| Agent list | about 2,200 |
| Hook output at start | about 300 (about 1,200 in Orderflow) |
| Git status, environment, output style, first message | about 2,300 |
| Tool definitions and anything not in the transcript | about 34,000, not explained |

The Vercel, Make and Adobe connectors are 77% of the tool-name list, about 30,000 tokens in every session and every subagent. A subagent has the same list, the same skill listing, `CLAUDE.md` and a tool-definition block of about 27,000, plus its own agent prompt: 6,000 to 10,000 tokens for the implementer and the gates. Explore is 63,000 because it skips `CLAUDE.md`, git status and the edit tools. The agent list, MCP instructions, start hooks and output style are main-session costs only. One workflow on disk started at 61,000, with a smaller connector set that day.

**The cuts**, with the saving of each:

1. Connectors off in build lanes: about 35,000 (Make and Adobe 15,000, Vercel 14,700, Gmail, Descript and others 5,000). Controls: `disableClaudeAiConnectors`, `ENABLE_CLAUDEAI_MCP_SERVERS=false`, `--strict-mcp-config`.
2. Non-lane skills set to `name-only` or `off`: about 9,000 (`skillOverrides`).
3. `omitClaudeMd: true` in the agent file for gates that get a full brief: about 11,800 in Orderflow.
4. A short `tools` list for the verifier and reviewer: up to 14,000.
5. Shorter agent prompts, the verify gate at 28,000 characters and the review gate at 25,000: 4,000 to 7,000 each.
6. MCP instructions, start-hook output and the agent list in the fast-lane build session: about 4,600 together.

With these, a fast-lane main session starts near 59,000, a careful-lane subagent near 35,000, and a read-only reviewer near 22,000 to 25,000. At a 300k window, compaction fires near 267k, which leaves a main session about 208k of work room and a subagent about 232k. That is 80% to 84% of the room version 1 had at 400k. The cuts support lowering the window; they do not make the room equal.

**What stays:** the Claude Code system prompt (about 12,000), the built-in tools a lane really uses (8,000 to 12,000), and the Desktop app's own tools and names (3,000 to 5,000 for names alone).

**What this does not settle.** The window stays at 400k until the audit shows start sizes falling, as "How every version 2 session stays under 300k tokens" decided. Not found, and each a question for the build stage: whether the connector controls reach the connectors the Desktop app supplies (the eight names in `disabledMcpServers` in `settings.json` did not remove Make or Adobe); whether a subagent's `tools` or `disallowedTools` removes tool names or skills from its context (Explore's did not); a cloud routine's start load; and a fresh `/context` table, which needs Abdul to run `/context` once in a main session. The saving from cuts 1 and 2 is unproven for subagents until one real run measures it.
