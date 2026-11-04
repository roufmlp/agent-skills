# Context size: what Claude Code offers to measure and cap it, fetched 2026-11-01

Ticket: `issues/34-context-size-facts.md`. Claude Code on this machine: 2.1.306.

Labels: **[docs]** the official docs say it; **[observed]** I measured it on this machine; **[inferred]** my own reasoning from the two, not stated anywhere.

Context size in this file means `input_tokens + cache_creation_input_tokens + cache_read_input_tokens` of one assistant response. That is the status line's formula (statusline.md, "context window fields").

## 1. Can a hook read the current context size?

- **[docs]** No hook event carries a context-size field on ordinary tool or prompt events. The common input fields are `session_id`, `prompt_id`, `transcript_path`, `cwd`, `scratchpad_dir`, `permission_mode`, `effort`, `hook_event_name`, plus `agent_id` and `agent_type` inside a subagent. https://code.claude.com/docs/en/hooks.md#common-input-fields
- **[docs]** Every event gets `transcript_path`, because it is a common field. The docs warn: "The transcript file is written asynchronously and may lag the in-memory conversation, so it may not yet include the current turn's most recent messages when a hook fires." Same section.
- **[docs]** Two events do carry a ready size, `context_tokens`, but neither is useful for a cap: `PreModelSwitch` ("the input, cache read, cache creation, and output tokens of the last response in the main conversation, combined") and `SessionStart` on `resume` or `fork` only. https://code.claude.com/docs/en/hooks.md#premodelswitch-input and #sessionstart-input
- **[docs]** The status line gets `context_window.total_input_tokens`, `context_window_size`, `used_percentage` and `current_usage`, but a status line script cannot block anything. `used_percentage` counts input tokens only, not output. https://code.claude.com/docs/en/statusline.md (fields table and "Context window fields")
- **[docs]** A `PostToolUse` hook on the `Agent` tool gets `tool_response.usage` and `totalTokens` for a foreground subagent, and these "cover the final request only". Background subagents return no usage fields. https://code.claude.com/docs/en/hooks.md#pretooluse-input (Agent tool table)
- **[observed]** The transcript format: each `type: "assistant"` line has `message.usage` with `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`, and a `cache_creation` split (`ephemeral_5m_input_tokens`, `ephemeral_1h_input_tokens`). One response can span several lines (one per content block, field `apiBlockIndex`) that repeat the same usage. Compactions are `type: "system"`, `subtype: "compact_boundary"`, with `compactMetadata.trigger` and `compactMetadata.preTokens`. Files: `~/.claude/projects/<project-dir>/<session-id>.jsonl`.
- **[observed]** Summing the three input fields on the last assistant line does give the context size. Across 282 compactions on this machine, `preTokens` minus that sum on the last assistant line before the boundary had a median of 1,720 tokens (10th percentile 568, 90th 6,750). The gap is the output plus the tool result not yet sent. Script: scratchpad `scripts/check_pre.py`.
- **[inferred]** So a command hook can compute the size by reading the tail of `transcript_path` and summing the last assistant usage. It sees the size as of the previous model response, at most one turn stale, and it misses the tool result about to be sent. Transcripts reach 48 MB here (90th percentile 2.6 MB, 4,805 Orderflow files), so the hook should read from the end of the file, not parse it whole.

## 2. Subagents and workflow agents

- **[docs]** "Hooks from settings files, managed policy settings, and plugins also run inside subagents. When a subagent calls a tool, tool events such as `PreToolUse` and `PostToolUse` fire the same configured hooks as in the main conversation, and the input carries the `agent_id` and `agent_type`." https://code.claude.com/docs/en/hooks.md#hook-locations ; also https://code.claude.com/docs/en/sub-agents.md#define-hooks-for-subagents
- **[docs]** For `SubagentStop`: "The `transcript_path` is the main session's transcript, while `agent_transcript_path` is the subagent's own transcript stored in a nested `subagents/` folder." https://code.claude.com/docs/en/hooks.md#subagentstop-input
- **[docs]** Subagent transcripts live at `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`. https://code.claude.com/docs/en/sub-agents.md (section on resuming subagents)
- **[docs]** "Each subagent runs in its own context window", sized by its own model. "Compaction triggers as the subagent's own context window fills, and `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` applies to subagents as well." https://code.claude.com/docs/en/sub-agents.md#auto-compaction
- **[docs]** A dynamic workflow's `agent()` "spawns one subagent"; the script "orchestrates subagents". https://code.claude.com/docs/en/workflows.md (script shape section). The workflows page does not say in words that hooks fire for workflow agents.
- **[observed]** Each subagent file has a sibling `agent-<id>.meta.json` with `agentType`, `spawnDepth`, `description`, `toolUseId`, `requestShape`, and sometimes `model`, `parentAgentId`, `workflowPhase`, `isFork`. 15 Orderflow subagents have `agentType: "workflow-subagent"` and a `workflowPhase`, stored in the same `subagents/` folder as others. Every line of a subagent file carries `agentId` and the parent's `sessionId`.
- **[observed]** The `agent_id` a hook receives has no `agent-` prefix: the `SubagentStop` hook `model-landed-check.py` logs values such as `a4cf1d41b04352095`, and the file is `agent-a4cf1d41b04352095.jsonl`. No main transcript holds a subagent's usage lines.
- **[inferred]** So a `PreToolUse` hook inside a subagent can find the subagent's own file as `<dir of transcript_path>/<session_id>/subagents/agent-<agent_id>.jsonl`, and read the subagent's size, not the parent's. This assumes `transcript_path` in a subagent's tool event is the parent's file, as it is for `SubagentStop`; the docs do not say so for tool events.

## 3. What a hook can do past a limit

- **[docs]** Block tool calls: `PreToolUse` exit 2, or `permissionDecision: "deny"`; the reason goes to Claude. `deny` wins over every other hook's decision. https://code.claude.com/docs/en/hooks.md#pretooluse-decision-control
- **[docs]** Stop before the next model call: `PostToolBatch` with `decision: "block"` or `continue: false` "stops the agentic loop before the next model call", and the message stays in the conversation. It fires once per batch. https://code.claude.com/docs/en/hooks.md#posttoolbatch-decision-control
- **[docs]** Block the next prompt: `UserPromptSubmit` exit 2 or `decision: "block"`; the prompt never reaches Claude. https://code.claude.com/docs/en/hooks.md#exit-code-2-behavior-per-event
- **[docs]** Stop Claude entirely: any hook may return `{"continue": false, "stopReason": "..."}`. https://code.claude.com/docs/en/hooks.md#json-output . The docs do not say whether `continue: false` from inside a subagent stops only that subagent or the whole session.
- **[docs]** `Stop` and `SubagentStop` can block stopping (force more work), not force a stop. `SubagentStart` cannot block a spawn. Same exit-code table.
- **[docs]** Ask for compaction: no hook output asks for compaction. Hooks can only block it (`PreCompact`, exit 2 or `decision: "block"`). https://code.claude.com/docs/en/hooks.md#precompact
- **[inferred]** Leave one write open: yes. `PreToolUse` receives `tool_name` and `tool_input`, so the script can deny every call except a `Write` or `Edit` whose `file_path` is the handoff path. The docs show matching on tool and input, not this exact pattern.
- **[docs]** Mechanical compaction instead of a hook: `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (100,000 to 1,000,000), the `autoCompactWindow` setting, `modelSettings.<model>.autoCompactWindow`, `/autocompact`, `--autocompact`, and `autoCompactWindow` in a subagent's frontmatter (100000 to 1000000, plain integer; `200k` reads as 200). The env var beats all others, including the subagent field. https://code.claude.com/docs/en/model-config.md#set-the-auto-compact-window ; https://code.claude.com/docs/en/sub-agents.md#set-the-auto-compact-window-for-one-subagent . Compaction summarises and goes on; it does not stop the agent.

## 4. Autocompact override and the window per model

- **[docs]** `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`: "Set the percentage (1-100) of the auto-compact window at which auto-compaction triggers." It can only lower the trigger ("values above the default percentage are ignored"), "applies only in sessions that compact before the model's context limit", and applies to main conversations and subagents. https://code.claude.com/docs/en/env-vars.md . The default percentage is not stated.
- **[docs]** The window that is the base for that percentage is set by the controls in section 3. "Whichever way you set the window, Claude Code caps it at the model's context window." model-config.md#set-the-auto-compact-window
- **[docs]** Windows: Fable 5.1, Fable 5, Sonnet 5 and later, Haiku 5.5, and Opus 4.7 and later run with 1M by default, no `[1m]` suffix needed. Opus 4.6 and Sonnet 4.6 have 200K, or 1M through `[1m]` (plan rules apply). `sonnet[1m]` and `opus[1m]` have no effect on models that already have native 1M. https://code.claude.com/docs/en/model-config.md#extended-context and #model-aliases
- **[docs]** Defaults: native-1M models compact "at about 967K tokens by default"; Opus 4.6 and Sonnet 4.6 without extended context compact at 200K. `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` holds native-1M models to 200K. model-config.md#default-auto-compact-thresholds
- **[observed]** The models Abdul's Orderflow agents used: `claude-opus-5-5`, `claude-opus-5`, `claude-sonnet-5-5` (transcript `message.model`). By the docs rule above, all three have a native 1M window. **[inferred]** "with and without the 1M window" no longer applies to these models: 200K comes only from `CLAUDE_CODE_DISABLE_1M_CONTEXT=1`.
- **[observed]** `~/.claude/settings.json` sets `modelSettings.claude-opus-5-5.autoCompactWindow: 400000`. No other compaction setting or env var is set. Orderflow auto-compactions: 172 fell between 350k and 400k (min 364,492, median 367,583, max 386,391), all in October and November; four in September fell at about 960k.
- **[inferred]** With a 400k window, compaction fires about 33k below it, the same gap as 967K on 1M. A window of 333k would then compact near 300k. This is fitted from one window value; I did not test another.
- **[observed]** The 400k window held for Opus 5.5 subagents too (parallel-hunt-finder: 50 of 60 compacted, all peaks 365k to 367k), but not for Opus 5 or Sonnet 5.5, which reached 934k and 776k.

## 5. Version 1's largest contexts per role

Source: 4,790 Orderflow transcripts with usage under `~/.claude/projects/-Users-roufmlp-code-orderflow*/`, dated 2026-09-09 to 2026-11-01 (`cleanupPeriodDays` is 90). Role is `agentType` from `meta.json`; main sessions are grouped together. "Peak" is the largest context of any one response in the file. Orderflow's run records (`.scratch/workflow-audit/runs.jsonl`, 75 rows) hold token and cache totals but no context size, so they could not answer this. Script: scratchpad `scripts/ctx.py` and `scripts/roles.py`. **[observed]** throughout.

| Role | n | p50 peak | p90 peak | max peak | over 300k | compacted |
| :- | -: | -: | -: | -: | -: | -: |
| main session | 514 | 235k | 415k | 966k | 180 | 42 |
| run-issues-implementer | 1260 | 200k | 365k | 934k | 252 | 28 |
| run-issues-finale | 68 | 301k | 597k | 649k | 34 | 2 |
| harden-issues-seam | 52 | 274k | 399k | 650k | 22 | 3 |
| general-purpose | 560 | 170k | 303k | 551k | 59 | 6 |
| Explore | 71 | 144k | 326k | 509k | 11 | 0 |
| run-issues-review-gate | 433 | 210k | 270k | 388k | 15 | 0 |
| run-issues-verify-gate | 434 | 241k | 307k | 377k | 57 | 1 |
| run-issues-review-gate-critical | 388 | 228k | 280k | 367k | 18 | 0 |
| parallel-hunt-finder | 60 | 365k | 366k | 367k | 59 | 50 |
| parallel-hunt-fixer | 128 | 217k | 350k | 366k | 21 | 9 |
| parallel-hunt-fix-gate | 73 | 215k | 285k | 362k | 4 | 1 |
| parallel-hunt-fix-gate-critical | 56 | 226k | 287k | 338k | 3 | 0 |
| harden-issues-attacker | 509 | 198k | 245k | 326k | 1 | 0 |
| promotion | 16 | 181k | 288k | 324k | 1 | 0 |
| workflow-subagent | 15 | 239k | 277k | 298k | 0 | 0 |
| parallel-hunt-claim-gate | 64 | 192k | 231k | 268k | 0 | 0 |

- Main sessions by first slash command: `/run-issues` 74 sessions, p90 705k, max 966k, 68 over 300k; `/to-issues` p90 540k; `/harden-issues` p90 415k; `/daily-brief` p90 417k; sessions with no command p90 344k.
- Implementers by model: Sonnet 5.5 p90 364k, max 776k; Opus 5.5 p90 360k, max 928k; Opus 5 p90 405k, max 934k.
- Starting size: the first response of a subagent already holds a median of 83k to 94k tokens (Explore 59k; main sessions 105k). That is the floor before the agent reads anything.

## Not found

- Whether `transcript_path` in a subagent's `PreToolUse` or `PostToolUse` input is the parent's file or the subagent's. The docs state it only for `SubagentStop`. Tool events get no `agent_transcript_path` in the docs.
- Whether hooks fire for workflow agents. The docs call them subagents but do not say it in words. Nothing on this machine logged a hook firing in one.
- Whether `continue: false` returned inside a subagent stops only that subagent or the whole session.
- Any hook output that asks for compaction, or any hook field that gives the model's context window size (only `SessionStart` can carry `model`, and not always).
- The default percentage that `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` cannot rise above, and the exact gap between the auto-compact window and the point where compaction fires.
- A setting that stops an agent, not compacts it, at a token count. None is documented; the controls found compact.
- Version 1 contexts before 2026-09-09: no transcripts that old remain under the Orderflow project folders.
