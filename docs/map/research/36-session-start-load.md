# What fills a session's first 100k tokens, fetched 2026-11-02

Ticket: `issues/36-session-start-load.md`. Claude Code on this machine: 2.1.306 (`claude --version`). Transcripts in this file were written by versions 2.1.215 to 2.1.309.

Labels: **[docs]** the official docs say it; **[observed]** I measured it on this machine; **[inferred]** my own reasoning from those, not stated anywhere.

Start load in this file means `input_tokens + cache_creation_input_tokens + cache_read_input_tokens` of the FIRST assistant response of a transcript file. It therefore includes the first user message (for a subagent, the brief). Scripts and data are in the scratchpad `/private/tmp/claude-501/-Users-roufmlp--claude-skills--claude-worktrees-wayfinder-workflow-map-83def8/4b66e725-9997-42f2-85df-aa6fe7015453/scratchpad` (`scripts/start.py`, `feat.py`, `ols.py`, `fit2.py`, `fit3.py`, `recon.py`, `perserver.py`, `misc.py`; data `rows.json`, `feats.json`).

## 0. What I could not do, and the method I used instead

- **[observed]** The planned differential runs (`claude -p ... --bare`, `--strict-mcp-config`, `--disable-slash-commands`, `--tools ""`) were impossible. `claude auth status` prints `"loggedIn": false`, and `claude -p "reply with the word ok" --output-format json` returns `"result":"Failed to authenticate: OAuth session expired and could not be refreshed"` with zero usage. No `ANTHROPIC_API_KEY` is set. I did not log in (that is Abdul's step). So no with/without token count was taken from a live run. Runs: two failed calls, files `scratchpad/runs/base.json` and `base2.json`.
- **[observed]** `claude mcp list` prints "No MCP servers configured". Every MCP tool seen in sessions here comes from the Desktop app (its built-in servers and the claude.ai connectors), not from the CLI's own config.
- **[observed]** What I used instead. Claude Code writes the text it injects into each transcript as `type: "attachment"` lines before the first response: `deferred_tools_delta`, `skill_listing`, `agent_listing_delta`, `mcp_instructions_delta`, `instructions` (CLAUDE.md and MEMORY.md, full text), `prompt_snapshot` (the system prompt), `session_context` (git status), `environment`, `hook_*`, `output_style_instructions`. This gives EXACT character counts per part for 8,644 transcript files (main sessions and subagents, 2026-07-21 to 2026-11-01). Token counts per part then come from three sources, in this order of strength: (a) one `/context` table that exists in an old transcript (section 2), (b) natural experiments between Claude Code versions that changed one part (sections 3 and 4), (c) a fitted characters-to-tokens ratio.
- **[observed]** The 15 `workflow-subagent` transcripts are not in `subagents/` but in `subagents/workflows/wf_*/agent-*.jsonl`. I measured them (section 6).

## 1. Observed start load by role (recent files)

Files modified since 2026-10-15, first assistant response. Script: `scripts/start.py`. **[observed]**

| Role | Project group | n | p10 | median | p90 |
| :- | :- | -: | -: | -: | -: |
| main session | Orderflow | 470 | 91,911 | 106,139 | 131,916 |
| main session | skills repo | 111 | 87,278 | 95,265 | 112,435 |
| main session | other | 502 | 73,764 | 87,798 | 106,212 |
| run-issues-implementer | Orderflow | 238 | 94,545 | 96,153 | 108,155 |
| run-issues-verify-gate | Orderflow | 82 | 95,949 | 99,478 | 109,357 |
| run-issues-review-gate | Orderflow | 92 | 97,046 | 99,261 | 110,780 |
| general-purpose | Orderflow | 174 | 88,101 | 90,653 | 104,290 |
| parallel-hunt-fixer | Orderflow | 128 | 88,921 | 90,003 | 91,586 |
| parallel-hunt-finder | Orderflow | 60 | 89,106 | 90,366 | 104,487 |
| harden-issues-attacker | Orderflow | 111 | 93,913 | 96,963 | 98,690 |
| Explore | Orderflow | 25 | 61,706 | 63,566 | 69,262 |
| general-purpose | skills repo | 25 | 80,746 | 81,723 | 82,853 |

- **[observed]** The ticket's numbers hold: main 106k (Orderflow), subagents 90k to 99k, Explore 64k.
- **[observed]** The first response includes the first user message, so the median hides the prompt. Cleanest main sessions (tiny first prompt, v2.1.299 and later, Opus 5.5) start at 102,965 to 109,024. A `/run-issues` batch session with a 77k-character first prompt starts at 149,052 (Orderflow, v2.1.299; `scripts/fit2.py` sample listing).
- **[observed]** The start load has grown with the version. Explore medians: 42,868 (v2.1.217, 2026-07-24) to 62,841 (v2.1.309, 2026-10-29). Main medians (all projects): 75,659 (v2.1.219) to 112,401 (v2.1.309). The text lists grew at the same time: deferred tool names 362 to 718 per session (Explore, same versions). Script: `feats.json` grouped by version.

## 2. The only direct per-part token table: one old `/context`

- **[observed]** One `/context` output survives in the transcripts, in the procurement worktree session `7ccb923a-...` (line 182, Claude Code 2.1.219, Opus 5, 2026-07-31). It is the single place Claude Code itself counted the parts. File: `~/.claude/projects/-Users-roufmlp-code-procurement--claude-worktrees-167-169-543461/7ccb923a-d216-470c-a0cf-666ede5582b0.jsonl`.

| Category (`/context`) | Tokens |
| :- | -: |
| System prompt | 5.9k |
| System tools | 10.9k |
| MCP tools (loaded) | 12k |
| MCP tools (deferred, full schemas, not in the total) | 192k |
| System tools (deferred, not in the total) | 15.5k |
| Custom agents (15 user agents) | 1.2k |
| Memory files (CLAUDE.md 1.7k, writingrules.md 2.5k, coderules.md 2.8k, project CLAUDE.md 839, MEMORY.md 3.4k) | 11.4k |
| Skills (36 listed in the table) | 9.9k |
| Messages | 117.4k |
| Total shown | 167.5k of 1m |

- **[observed]** That session's own start attachments: 375 deferred names (20,214 chars), 172 skills (29,963 chars), 21 agent types (5,697 chars), MCP instructions 8,607 chars, first response 79,710 tokens.
- **[inferred]** The skills row gives a ratio: 29,963 characters of listing for 9.9k tokens is 0.33 tokens per character (3.0 characters per token).
- **[inferred]** The "(deferred)" rows are what the schemas would cost if loaded; they are not what a session pays at start. At start a deferred tool costs its name only (section 3).
- **[inferred]** The "MCP tools 12k" loaded row in that table is probably tools Claude loaded through `ToolSearch` during the session, not an upfront cost. The docs do not say.
- Limits: this is one session, version 2.1.219, a different skill set and a much smaller CLAUDE.md. Use it as a sanity check, not a current number.

## 3. The deferred tool-name list is the largest single part

- **[docs]** "Only tool names and server instructions load at session start, so adding more MCP servers has minimal impact on your context window." https://code.claude.com/docs/en/mcp.md#scale-with-mcp-tool-search . Tool search is on by default (`ENABLE_TOOL_SEARCH` unset: "All MCP tools deferred and loaded on demand"). https://code.claude.com/docs/en/mcp.md#configure-tool-search
- **[docs]** costs.md says the same: "MCP tool definitions are deferred by default, so only tool names and server instructions enter context". https://code.claude.com/docs/en/costs.md#reduce-mcp-server-overhead
- **[observed]** The names list is not minimal here. In this session (v2.1.309): 729 deferred names, 40,499 characters (`deferred_tools_delta.addedNames`, identical text in `addedLines`). In every subagent file I opened the same list is in the system part: the request outline of subagent `agent-a01cd821a80b5e502` shows a system block of 74,770 characters with a part of 41,376 characters, which matches the names list (41,228 characters with separators) and the skill listing (29.8k) plus a 2.7k system prompt. (`prefix.json`, field `outlines`.)
- **[observed]** By server in this session (`scripts/perserver.py`; server names inferred from tool names, the transcript only holds the UUID prefix):

| Server prefix | Looks like | Names | Chars |
| :- | :- | -: | -: |
| `e2e88e5c-...` | Vercel | 244 | 15,679 |
| `4a914dfe-...` | Make | 143 | 9,269 |
| `f8e28b12-...` | Adobe | 111 | 6,992 |
| `6c49fefe-...` | Gmail | 30 | 1,738 |
| `6c81ec09-...` | Descript | 17 | 1,001 |
| `computer-use`, `claude-in-chrome`, `Control_Chrome` | Desktop built-ins | 59 | 2,055 |
| `ccd_*` (session, sidebar, host, view, window, pr, settings...) | Desktop host | 63 | 2,197 |
| Drive, Calendar, Docs, Context7, scheduled-tasks, terminal, mcp-registry, iOS simulator | | 41 | 2,043 |
| 21 built-in tool names | | 21 | 254 |

  The three big connectors are 498 of 729 names and 31,940 of 41,228 characters (77%).
- **[observed]** Cost per character, from a natural experiment on Explore subagents, which have no CLAUDE.md, no git status and a constant 3,257-character system prompt. Between v2.1.270 and v2.1.280 the deferred list grew from 467 to 659 names (25,294 to 36,886 characters, +11,592) while the skill listing (28.8k characters) and prompt stayed equal; the median start load grew from 49,333 to 60,324 (+10,991). That is 0.95 tokens per character, about 57 tokens per name. A fit across all Explore files from v2.1.266 on (n=74, `scripts/fit3.py`) gives a slope of 0.937 tokens per character; the same fit on general-purpose subagents (n=543) gives 1.008.
- **[inferred]** So the list costs about 0.94 tokens per character (range 0.8 to 1.0), or 38k tokens (32k to 41k) for 40,499 characters. The range is wide for two reasons: the names carry UUIDs, which tokenise at about one token per one to two characters, and the v2.1.280 step also brought three Adobe tools that load upfront (their schemas are in the same step), so the true slope may be near the low end. The text may also appear twice on the wire (a `defer_loading` tool entry plus the listing); the transcripts cannot show that.
- **[inferred]** Per server at 0.94: Vercel 14.7k, Make 8.7k, Adobe 6.6k, Gmail 1.6k, Descript 0.9k. The three big connectors cost about 30k tokens in every main session and in every subagent on this laptop.
- **[observed]** The deferred list does not shrink for a restricted built-in tool set: Explore (tools "all except Agent, Artifact, Edit, Write, NotebookEdit") still lists 710 names. A `tools` allowlist therefore did not remove MCP names in the one case I can see. I found no subagent with an MCP-restricting `tools` or `disallowedTools` field to test that.
- **[observed]** `~/.claude/settings.json` holds a top-level `disabledMcpServers` with 8 names (`claude.ai Adobe for creativity`, `claude.ai Make`, `claude.ai Descript`, `claude.ai Canva`, `claude.ai Slack`, `claude.ai Notion`, `claude.ai Cloudflare Developer Platform`, `claude.ai HyperFrames by HeyGen`). The Make and Adobe tools are still in this session's deferred list. **[docs]** `disabledMcpServers` "is recorded per project in `~/.claude.json`, written when you toggle a server in `/mcp`" (https://code.claude.com/docs/en/mcp.md, MCP server status and disable section), and it is not in the settings index of https://code.claude.com/docs/en/settings-reference.md . **[observed]** 0 of 809 projects in `~/.claude.json` have a non-empty `disabledMcpServers`. **[inferred]** The key in `settings.json` may do nothing, or the Desktop app may supply these connectors outside it. I did not establish which.

## 4. Part-by-part: a main session (this session, v2.1.309, Opus 5.5, skills repo)

Observed start load of this session's first response: **106,727**. Characters are exact; tokens use the ratio in the last column. Script: `scripts/misc.py`, `scripts/recon.py`.

| Part | Chars [observed] | Tokens | Label | Ratio / source |
| :- | -: | -: | :- | :- |
| Deferred tool names (729) | 40,499 | about 38,000 (32k to 41k) | [inferred] | 0.94 per char, section 3 |
| Skill listing (77 skills) | 29,842 | about 9,900 | [inferred] | 0.33 per char, from section 2 |
| System prompt (Claude Code default plus Desktop additions) | 35,060 | about 12,300 | [inferred] | 0.35 per char, section 5 |
| CLAUDE.md `~/.claude/CLAUDE.md` plus MEMORY.md (2 files) | 12,683 + 632 | about 4,700 | [inferred] | 0.35 per char |
| Agent listing (22 types) | 6,180 | about 2,200 | [inferred] | 0.35 per char |
| MCP server instructions (computer-use 6,381; claude-in-chrome 1,022) | 7,403 | about 2,600 | [inferred] | 0.35 per char |
| SessionStart hook output (3 hooks) | about 800 | about 300 | [inferred] | 0.35 per char |
| Git status and user email (`session_context`) | 2,076 | about 700 | [inferred] | 0.35 per char |
| Environment, model, date, org id | about 900 | about 300 | [inferred] | 0.35 per char |
| Output style "Concise" instructions | about 1,600 | about 600 | [inferred] | 0.35 per char |
| First user message | 2,100 | about 700 | [inferred] | 0.35 per char |
| Sum of the above | | about 72,400 | | |
| **Remainder: built-in tool definitions, MCP tools loaded upfront, anything not in the transcript** | | **about 34,300** | [inferred] | observed total minus the sum |

- **[observed]** The tool definitions are not in the transcript. The `prefix.json` of Desktop subagents lists 45 tools sent upfront: 9 built-in (`Agent`, `Artifact`, `Bash`, `Edit`, `Read`, `SearchPlugins`, `Skill`, `ToolSearch`, `Write`), 1 `SubagentHandback`, and 35 MCP tools that the Desktop app loads upfront (18 `Claude_Browser`, 6 `ccd_session`/`ccd_turn`, 3 Adobe, 3 `1a59c906` docs tools, 2 `visualize`, `terminal`, iOS simulator). The 34k remainder is mostly these schemas. The only direct measure, section 2, gave 10.9k for system tools and 12k for loaded MCP tools in July. So 11k to 23k of the remainder is supported; the rest (about 11k to 23k) is **not explained**.
- **[observed]** Orderflow main sessions (median 106,139) differ from this one in three places (`scripts/misc.py`): four instruction files instead of two (global CLAUDE.md 11,865 chars, worktree CLAUDE.md 7,890, MEMORY.md 6,487, parent-checkout CLAUDE.md 8,351; total about 32,700 chars, about 11,400 tokens), MCP instructions of 14,700 to 16,400 chars (about 5,500 tokens), and SessionStart hook output with a median of 3,322 chars (p90 3,468, max 3,846; about 1,200 tokens).

## 5. The characters-to-tokens ratio

- **[observed]** Across Opus 5.5 main sessions on v2.1.299 or later (n=161, deferred list and skill listing nearly constant) a fit of start load on the varying text (instructions, MCP instructions, hooks, first prompt, system prompt) with ONE ratio gives 0.355 tokens per character (R squared 0.80). The same single-ratio fit on non-Explore subagents (n=1,222) gives 0.373. Script: `scripts/fit2.py`. Separate per-part coefficients were unstable (collinear), so only the pooled ratio is used.
- **[inferred]** I use 0.35 for English text parts and 0.33 for the skill listing (from section 2). The sensitivity is about plus or minus 6% on each text part (0.33 to 0.37).

## 6. Part-by-part: subagents and the workflow agent

Medians of recent files, v2.1.299 or later (2026-10-17 on). Text tokens at 0.94 (deferred), 0.33 (skills), 0.35 (the rest). Script: `scripts/recon.py`. **[observed]** for the first three numeric columns, **[inferred]** for the token columns.

| Role | n | Observed start | Deferred names (chars) | Skill listing (chars) | Agent system prompt (chars) | CLAUDE.md and MEMORY (chars) | Est. text tokens | Remainder (tools etc.) |
| :- | -: | -: | -: | -: | -: | -: | -: | -: |
| general-purpose, Orderflow | 161 | 90,636 | 40,292 | 29,842 | 2,714 | 33,859 | 63,270 | 27,365 |
| run-issues-implementer | 204 | 95,982 | 39,776 | 29,900 | 17,764 | 33,859 | 66,928 | 29,053 |
| run-issues-verify-gate | 78 | 100,151 | 39,692 | 29,900 | 28,064 | 34,474 | 70,666 | 29,484 |
| run-issues-review-gate | 76 | 98,875 | 39,776 | 29,900 | 24,605 | 33,859 | 69,369 | 29,505 |
| parallel-hunt-fixer | 177 | 90,506 | 39,692 | 29,991 | 6,874 | 31,360 | 63,131 | 27,374 |
| parallel-hunt-fix-gate | 104 | 89,915 | 39,692 | 29,991 | 6,639 | 31,360 | 62,985 | 26,930 |
| harden-issues-attacker | 97 | 97,007 | 39,776 | 29,987 | 24,918 | 32,819 | 68,927 | 28,079 |
| general-purpose, skills repo (me) | 1 | 83,958 | 40,400 | 29,842 | 2,735 | 13,315 | 56,100 | 27,900 |
| Explore, Orderflow | 16 | 62,799 | 39,773 | 29,989 | 3,257 | 0 | 49,825 | 12,973 |
| workflow-subagent (v2.1.280, 2026-10-07) | 15 | 60,991 | 23,848 | 29,953 | 1,870 | 26,978 | 44,100 | 16,900 |

- **[observed]** The remainder is almost the same for ten different subagent types: 26.7k to 29.5k. **[inferred]** So it behaves as one constant block, the tool definitions of an "All tools" subagent, plus a small error from the ratios.
- **[observed]** Explore's remainder is 13.0k, 14.4k lower than general-purpose. Explore removes `Agent`, `Artifact*`, `Edit`, `Write`, `NotebookEdit`. **[inferred]** Those tools' definitions are about 14k tokens, or part of that and part of the 35 upfront MCP tools if Explore does not get them. I cannot separate the two.
- **[observed]** The agent's own system prompt is a real cost: the `prompt_snapshot` is 17,764 chars for run-issues-implementer (about 6,200 tokens), 24,605 for the review gate, 28,064 for the verify gate (about 9,800 tokens), against 2,714 for general-purpose.
- **[observed]** Subagent files have NO `agent_listing_delta`, `mcp_instructions_delta`, `hook_*`, `output_style_*` attachments. They do have the skill listing, the full deferred list, and (except Explore) `instructions`, `session_context` and `environment`. So the agent list, MCP server instructions, SessionStart hook output and output style are main-session costs only.
- **[observed]** A general-purpose subagent loads MEMORY.md too (my own file lists `~/.claude/CLAUDE.md` 12,683 and the project `MEMORY.md` 632 as `instructions`). **[docs]** The subagent docs say "the main conversation's auto memory isn't loaded". The docs may mean the subagent `memory` field. The transcript is the stronger evidence for what loads.
- **[docs]** What a subagent inherits: no system prompt of Claude Code ("only this system prompt plus basic environment details"); CLAUDE.md hierarchy yes except built-in Explore and Plan; git status snapshot yes except Explore and Plan; hooks from settings and plugins yes; MCP tools yes (background subagents keep every MCP tool); skills only listed ones preloaded but unlisted ones callable through `Skill`; not output style, not conversation history. https://code.claude.com/docs/en/sub-agents.md (inheritance section; "What loads at startup")
- **[observed]** Workflow agent: 15 transcripts, one workflow (`wf_2e88c614-66a`), one day, v2.1.280, Opus 5.5: start load 60,985 to 61,340, median 60,991. Its deferred list was shorter (547 names, 23,848 chars) because the connector set was smaller that day, which is why it is 30k below an Orderflow subagent today. It loaded CLAUDE.md files (26,978 chars). Workflow agents are subagents, so the same cuts apply. **[inferred]** Today's workflow agent would start near 90k like other subagents (60,991 plus about 16k tokens for 170 more names plus the larger tool block); I did not measure a current one.

## 7. Cloud routine session

- **[docs]** A scheduled task (formerly routine) "run[s] autonomously as full Claude Code cloud sessions". It uses the cloned repository, the cloud environment (network, variables, setup script) and the connectors you include. "All of your connected MCP connectors are included by default. Remove any the task doesn't need." https://code.claude.com/docs/en/routines.md ("Review connectors"; "Connectors")
- **[docs]** What the cloud session does NOT get: your user `~/.claude/CLAUDE.md`, your user `~/.claude/skills/`, `agents/`, `commands/`, plugins enabled only in user settings, user-level SessionStart hooks, MCP servers added with `claude mcp add` at local or user scope. What it gets: the repo's `CLAUDE.md` and committed `.claude/`, and "skills you enable on claude.ai". https://code.claude.com/docs/en/cloud-environments.md#what-carries-over-from-your-setup
- **[inferred]** So a cloud routine does not pay for Abdul's global CLAUDE.md (12.7k chars here), user skills, user agents or SessionStart hooks. It does pay for the connectors left on the routine (the deferred names cost, section 3), the skill listing of any skills enabled on claude.ai (the 23 `anthropic-skills` here, 12.7k chars) and the Claude Code system prompt.
- **Not found:** a measured start load for a cloud session, its tool definitions, and whether the Desktop-only servers (`ccd_*`, `computer-use`, `Claude_Browser`) exist there. No transcript of a cloud routine run is on this machine.

## 8. Cuts version 2 can make

Lanes: fast-lane build session (main, one auto-mode build session), careful-lane implementer, verifier and reviewer (subagents), brainstorm routine (cloud), evening check (the scheduled local session; **[inferred]** it runs in a Desktop app session and loads the same Desktop MCP set). Token savings use the ratios in section 5 and the 0.94 deferred slope, so they are **[inferred]** from **[observed]** character counts.

| # | Part | Cut | Saves (tokens) | Control (exact name) | Lanes | Label |
| :- | :- | :- | -: | :- | :- | :- |
| 1 | Make and Adobe connector names | Turn both off for build lanes | about 15,000 (13.7k to 16.3k) | `disableClaudeAiConnectors` setting (any settings file, so it can be per product repo); `ENABLE_CLAUDEAI_MCP_SERVERS=false` env var; `/mcp` toggle (writes `disabledMcpServers` per project in `~/.claude.json`); `--strict-mcp-config` with `--mcp-config` | fast-lane build, careful-lane main, evening check | savings [inferred]; names [docs] https://code.claude.com/docs/en/mcp.md#disable-claude-ai-connectors , env-vars.md, settings-reference.md |
| 2 | Vercel connector names | Off except where the lane deploys | about 14,700 | same controls as row 1 | careful-lane subagents; fast lane only if it deploys through the connector | [inferred] |
| 3 | Gmail, Descript, Drive, Calendar and other connectors | Off in build lanes | about 5,000 | same controls | all build lanes | [inferred] |
| 4 | Skill listing | Set non-lane skills to `"name-only"` or `"off"`: 77 skills at 29,842 chars become 1,933 chars of names | about 9,200 (name-only for all); about 5,400 if only the 35 non-user skills go | `skillOverrides` in settings (`on`, `name-only`, `user-invocable-only`, `off`; plugin skills are not affected, manage with `/plugin` and `enabledPlugins`); `skillListingMaxDescChars`; `skillListingBudgetFraction`; env `SLASH_COMMAND_TOOL_CHAR_BUDGET`; frontmatter `disable-model-invocation: true` removes a skill's description from context; `--disable-slash-commands` ("Disable all skills and commands", `claude --help`) | all lanes (subagents also carry the listing) | savings [inferred]; controls [docs] https://code.claude.com/docs/en/skills.md#skill-descriptions-are-cut-short and #override-skill-visibility-from-settings |
| 5 | CLAUDE.md and MEMORY.md in subagents | Skip the hierarchy for gates that get a full brief | about 11,800 in Orderflow (33,859 chars); about 4,700 in the skills repo | agent frontmatter `omitClaudeMd: true`; `claudeMdExcludes` (path or glob, any settings layer); `autoMemoryEnabled: false` or `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` for MEMORY.md (about 2,300 in Orderflow); `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` turns off all of it | careful-lane implementer, verifier, reviewer | savings [inferred]; fields [docs] https://code.claude.com/docs/en/sub-agents.md (frontmatter table), memory.md#exclude-specific-claude-md-files , env-vars.md |
| 6 | Built-in tool definitions in read-only roles | Give verifier and reviewer a short `tools` list | up to about 14,000 (Explore's remainder is 13.0k against 27.4k for an "All tools" agent) | agent frontmatter `tools` (allowlist) and `disallowedTools`; `--tools "Read,Bash"` ("Specify the list of available tools from the built-in set", `claude --help`); `--restricted` | careful-lane verifier and reviewer | difference [observed], cause [inferred]; fields [docs] sub-agents.md |
| 7 | Agent system prompt text | Shorten the agent bodies: verify gate 28,064 chars, review gate 24,605, attacker 24,918, implementer 17,764 | about 4,000 to 7,000 per agent if cut to 6,000 chars | edit the agent files (plain text) | careful lane | [inferred] |
| 8 | MCP server instructions (main only) | Drop `computer-use` and `claude-in-chrome` where no browser work happens | about 2,600 (this session); about 5,500 (Orderflow main) | disable the server; cap with `CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH` (default 4,096 for upfront instructions; needs v2.1.280 or later) | fast-lane build without browser steps | [inferred]; env [docs] https://code.claude.com/docs/en/mcp.md#for-mcp-server-authors and env-vars.md |
| 9 | SessionStart hook output (main only) | Print one line, not 3,322 characters (median in Orderflow) | about 1,000 | edit the three SessionStart hooks (`machine-preflight.py session`, `worktree-snapshot-notice.py`, `worktree-base-drift.py`); `disableAllHooks` would also drop the guards | all main sessions | [inferred] |
| 10 | Agent listing (main only) | Keep v2 agents in the plugin loaded by the careful lane only; the 16 user agent descriptions are 2,959 of 6,180 chars | about 1,000 | agent file location (user dir against plugin or project); `--agents` | fast-lane build | [inferred] |
| 11 | Git status and git instructions | Remove the snapshot and the built-in commit and PR text | about 600 for the snapshot (1,780 chars); the size of the built-in git text was not measured | `includeGitInstructions: false`; env `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1` | any lane that uses its own git skill | snapshot [observed]; controls [docs] env-vars.md |
| 12 | Tools that load upfront | Check which MCP tools the Desktop app loads upfront (35 here) | not measured; part of the 27k to 34k remainder | `alwaysLoad: false` per server defers even tools the author marked upfront (needs v2.1.287 or later); `ENABLE_TOOL_SEARCH` values `true`, `auto`, `auto:N`, `false` | all lanes | [docs] https://code.claude.com/docs/en/mcp.md#exempt-a-server-from-deferral and #configure-tool-search |

For subagents specifically, **[docs]** the frontmatter has `tools`, `disallowedTools` ("removed from inherited or specified list"; the docs example is `disallowedTools: mcp__github`), `mcpServers`, `skills`, `omitClaudeMd`, `autoCompactWindow`, `model`, `maxTurns`. The subagent docs say `Skill` can be omitted from `tools` or added to `disallowedTools` to block skill use. **[inferred]** None of the docs I read says whether those fields also remove the names from the subagent's deferred list or the skill listing from its prompt. In the one case I can check, Explore's reduced tool set kept all 710 names and the full skill listing (section 3 and 6). Treat rows 1 to 3 and 4 as certain for the main session and unproven for subagents until one real subagent run with `disallowedTools: mcp__<server>` is measured.

What stays, because it cannot be cut by a file setting:

- **[observed]** The Claude Code system prompt: 33,000 to 35,000 chars in main sessions (about 12,000 tokens), with a 27,013-character block that never changed across the sessions I opened. Only `--system-prompt` replaces it, and I could not test what that saves.
- **[observed]** The Desktop host's own tools (`ccd_*`, `Claude_Browser`, `terminal`, `visualize`) and their names: about 3,000 to 5,000 tokens of names and most of the upfront MCP schemas. Whether a setting removes them is **not found**.
- **[inferred]** The built-in tools a lane really uses (`Bash`, `Read`, `Edit`, `Write`, `Skill`, `ToolSearch`), a core of roughly 8,000 to 12,000 tokens (the July `/context` showed 10.9k for system tools).
- **[observed]** Environment, date and model lines, about 300 tokens.
- The user's first message, and for a subagent the brief.

## 9. How low can the start load go

All numbers **[inferred]** from the tables above.

- Main session, fast lane, with rows 1, 2, 3 (connectors off: about 35k), 4 (skills name-only: 9k), 8 and 9 (about 3.6k): 106.7k minus 47.6k is about **59k**. With a trimmed global CLAUDE.md the rest stays near 4.7k (this session's file).
- Main session, Orderflow-style (four instruction files): the same cuts take 106k to about **60k** before the 11.4k of instruction files, and about 49k if those shrink to the 4.7k global file.
- Careful-lane subagent: 90.6k, minus connectors (35k), skills name-only (9k), `omitClaudeMd` (11.8k): about **35k**. A read-only reviewer with a short `tools` list: about **22k to 25k**.
- Explore today is 62.8k; with rows 1 to 4 it would be about 18k.
- **[inferred]** Compaction fires about 33k below the window (file `34-context-size-facts.md`, section 4: 172 compactions between 364k and 386k at 400k). At a 300k window that is about 267k. Work room before compaction, main: now 367k minus 106k = 261k at 400k; after cuts 267k minus 59k = **208k** at 300k. For a subagent: now 367k minus 91k = 276k; after cuts 267k minus 35k = **232k**. So after the cuts a 300k window gives 80% to 84% of the work room that version 1 had at 400k. The cuts support lowering the window; they do not make the room equal. The size of the saving depends on rows 1 to 3 working on the Desktop app's connectors, which section 3 did not prove.

## Not found

- A with/without token count from a live run (`--bare`, `--strict-mcp-config`, `--disable-slash-commands`, `--tools`, `--setting-sources`): not possible, the CLI is logged out (section 0). Every per-part token count except the July `/context` is derived, not measured.
- A current `/context` table. The only one on the machine is from v2.1.219 (section 2). A fresh one needs a person to run `/context` once in a main session and once through a subagent.
- The size of the built-in tool definitions and of the 35 upfront MCP tools. The 27k to 34k remainder is their upper bound, not their measure.
- Whether the deferred name list is billed once or twice on the wire.
- Whether `disableClaudeAiConnectors`, `ENABLE_CLAUDEAI_MCP_SERVERS=false` or `--strict-mcp-config` removes the Desktop app's connectors (Vercel, Make, Adobe...) from a Desktop-app session. The tool names there have UUID prefixes, not the `claude.ai` names that `disabledMcpServers` uses.
- Why the 8-name `disabledMcpServers` in `~/.claude/settings.json` did not remove Make and Adobe.
- Whether a subagent's `tools`, `disallowedTools: mcp__<server>`, `mcpServers` or an omitted `Skill` tool removes names from its deferred list or the skill listing from its prompt.
- How `skillListingBudgetFraction` and the 1% rule relate to the auto-compact window (400k) or the model window (1M). The listing here is 29,842 chars, so the budget did not bite; the docs say "1% of the model's context window" with a fallback of 8,000 characters (env-vars.md, `SLASH_COMMAND_TOOL_CHAR_BUDGET`).
- A cloud routine's measured start load, tool set, or whether Desktop-only servers exist there (section 7).
- A current workflow-agent start load (only the 2026-10-07 workflow is on disk).
- The size of the "built-in commit and PR instructions" that `includeGitInstructions: false` removes.
- What `--system-prompt` or `--bare` saves; `--help` says `--bare` skips hooks, LSP, plugin sync, auto-memory and CLAUDE.md discovery but I could not run it.
- Docs anchors I could not read in full: the WebFetch tool summarised long pages (mcp.md, skills.md, env-vars.md, settings-reference.md), so every quote above was returned by that summary; the persisted copies are in the session's `tool-results` folder. The `disabledMcpServers` section of mcp.md has no anchor I could confirm.

## /context on 2026-11-03

Run in a main session in the Desktop app, working directory `~/code/orderflow`, model claude-fable-5-1, before the first user message.

**Tokens:** 92.8k / 400k (23%)

### Estimated usage by category

| Category | Tokens | Percentage |
|----------|--------|------------|
| System prompt | 13.4k | 3.3% |
| System tools | 16.9k | 4.2% |
| MCP tools | 33.2k | 8.3% |
| MCP server instructions | 4.5k | 1.1% |
| MCP tools (deferred) | 134k | 33.5% |
| System tools (deferred) | 23.4k | 5.9% |
| Custom agents | 1.3k | 0.3% |
| Memory files | 13.5k | 3.4% |
| Skills | 9.9k | 2.5% |
| Messages | 190 | 0.0% |
| Free space | 274.2k | 68.5% |
| Autocompact buffer | 33k | 8.3% |

### MCP Tools

| Tool | Server | Tokens |
|------|--------|--------|
| mcp__1a59c906-04da-521d-bda7-7f71b9f9e01c__batch | 1a59c906-04da-521d-bda7-7f71b9f9e01c | 150 |
| mcp__1a59c906-04da-521d-bda7-7f71b9f9e01c__create | 1a59c906-04da-521d-bda7-7f71b9f9e01c | 229 |
| mcp__1a59c906-04da-521d-bda7-7f71b9f9e01c__delete | 1a59c906-04da-521d-bda7-7f71b9f9e01c | 294 |
| mcp__1a59c906-04da-521d-bda7-7f71b9f9e01c__export | 1a59c906-04da-521d-bda7-7f71b9f9e01c | 426 |
| mcp__1a59c906-04da-521d-bda7-7f71b9f9e01c__guide | 1a59c906-04da-521d-bda7-7f71b9f9e01c | 188 |
| mcp__1a59c906-04da-521d-bda7-7f71b9f9e01c__query | 1a59c906-04da-521d-bda7-7f71b9f9e01c | 163 |
| mcp__1a59c906-04da-521d-bda7-7f71b9f9e01c__read | 1a59c906-04da-521d-bda7-7f71b9f9e01c | 288 |
| mcp__1a59c906-04da-521d-bda7-7f71b9f9e01c__update | 1a59c906-04da-521d-bda7-7f71b9f9e01c | 265 |
| mcp__27fc586e-5b4e-4b09-8dc9-41fc3af0785c__query-docs | 27fc586e-5b4e-4b09-8dc9-41fc3af0785c | 764 |
| mcp__27fc586e-5b4e-4b09-8dc9-41fc3af0785c__resolve-library-id | 27fc586e-5b4e-4b09-8dc9-41fc3af0785c | 1.1k |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__apply_sensitive_message_label | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 425 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__apply_sensitive_thread_label | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 359 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__create_draft | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 1.7k |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__create_label | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 1.9k |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__delete_draft | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 144 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__delete_label | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 129 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__forward | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 1.6k |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__get_draft | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 711 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__get_message | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 1.1k |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__get_thread | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 1.1k |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__label_message | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 456 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__label_thread | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 470 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__list_drafts | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 2.1k |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__list_labels | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 378 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__mark_message_spam | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 162 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__mark_thread_spam | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 235 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__reply | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 1.8k |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__search_threads | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 3.5k |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__send_message | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 2k |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__trash_message | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 310 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__trash_thread | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 304 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__unlabel_message | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 357 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__unlabel_thread | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 435 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__unmark_message_spam | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 165 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__unmark_thread_spam | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 143 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__untrash_message | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 166 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__untrash_thread | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 144 |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__update_draft | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 1.8k |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__update_label | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 1.7k |
| mcp__6c49fefe-f567-4c05-b17e-91831bf2e1ec__update_message_labels | 6c49fefe-f567-4c05-b17e-91831bf2e1ec | 448 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__cancel_job | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 122 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__export_timeline | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 1k |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__export_transcript | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 591 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__file_upload_ui | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 645 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__get_drive_info | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 135 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__get_project | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 318 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__import_drive_media | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 801 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__import_media | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 2.7k |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__import-claude-motion-from-url | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 356 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__list_folders | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 234 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__list_jobs | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 197 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__list_projects | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 764 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__prompt_project_agent | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 1.1k |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__publish_project | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 913 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__report_upload_status | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 626 |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__search_drive | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 1.2k |
| mcp__6c81ec09-1a90-4182-a595-ad2a4c1059e5__wait_for_job | 6c81ec09-1a90-4182-a595-ad2a4c1059e5 | 654 |
| mcp__a8cd5330-4c56-4a11-959f-fdcc94b20efc__create_event | a8cd5330-4c56-4a11-959f-fdcc94b20efc | 3.4k |
| mcp__a8cd5330-4c56-4a11-959f-fdcc94b20efc__delete_event | a8cd5330-4c56-4a11-959f-fdcc94b20efc | 306 |
| mcp__a8cd5330-4c56-4a11-959f-fdcc94b20efc__get_event | a8cd5330-4c56-4a11-959f-fdcc94b20efc | 200 |
| mcp__a8cd5330-4c56-4a11-959f-fdcc94b20efc__list_calendars | a8cd5330-4c56-4a11-959f-fdcc94b20efc | 329 |
| mcp__a8cd5330-4c56-4a11-959f-fdcc94b20efc__list_events | a8cd5330-4c56-4a11-959f-fdcc94b20efc | 1.3k |
| mcp__a8cd5330-4c56-4a11-959f-fdcc94b20efc__respond_to_event | a8cd5330-4c56-4a11-959f-fdcc94b20efc | 467 |
| mcp__a8cd5330-4c56-4a11-959f-fdcc94b20efc__search_events | a8cd5330-4c56-4a11-959f-fdcc94b20efc | 223 |
| mcp__a8cd5330-4c56-4a11-959f-fdcc94b20efc__suggest_time | a8cd5330-4c56-4a11-959f-fdcc94b20efc | 733 |
| mcp__a8cd5330-4c56-4a11-959f-fdcc94b20efc__update_event | a8cd5330-4c56-4a11-959f-fdcc94b20efc | 2.7k |
| mcp__afa62cf7-65b1-4cd5-b07e-632be372f864__copy_file | afa62cf7-65b1-4cd5-b07e-632be372f864 | 535 |
| mcp__afa62cf7-65b1-4cd5-b07e-632be372f864__create_file | afa62cf7-65b1-4cd5-b07e-632be372f864 | 1.2k |
| mcp__afa62cf7-65b1-4cd5-b07e-632be372f864__download_file_content | afa62cf7-65b1-4cd5-b07e-632be372f864 | 451 |
| mcp__afa62cf7-65b1-4cd5-b07e-632be372f864__get_file_metadata | afa62cf7-65b1-4cd5-b07e-632be372f864 | 503 |
| mcp__afa62cf7-65b1-4cd5-b07e-632be372f864__get_file_permissions | afa62cf7-65b1-4cd5-b07e-632be372f864 | 132 |
| mcp__afa62cf7-65b1-4cd5-b07e-632be372f864__list_recent_files | afa62cf7-65b1-4cd5-b07e-632be372f864 | 670 |
| mcp__afa62cf7-65b1-4cd5-b07e-632be372f864__read_file_content | afa62cf7-65b1-4cd5-b07e-632be372f864 | 819 |
| mcp__afa62cf7-65b1-4cd5-b07e-632be372f864__search_files | afa62cf7-65b1-4cd5-b07e-632be372f864 | 1.2k |
| mcp__afa62cf7-65b1-4cd5-b07e-632be372f864__share_file | afa62cf7-65b1-4cd5-b07e-632be372f864 | 600 |
| mcp__afa62cf7-65b1-4cd5-b07e-632be372f864__trash_file | afa62cf7-65b1-4cd5-b07e-632be372f864 | 153 |
| mcp__afa62cf7-65b1-4cd5-b07e-632be372f864__update_file | afa62cf7-65b1-4cd5-b07e-632be372f864 | 1.2k |
| mcp__ccd_connectors__reconnect_session_connector | ccd_connectors | 315 |
| mcp__ccd_connectors__session_connectors_status | ccd_connectors | 401 |
| mcp__ccd_connectors__set_session_connector_enabled | ccd_connectors | 497 |
| mcp__ccd_directory__change_directory | ccd_directory | 340 |
| mcp__ccd_directory__request_directory | ccd_directory | 263 |
| mcp__ccd_host__clean_up_worktrees | ccd_host | 647 |
| mcp__ccd_host__discard_kept_worktree | ccd_host | 585 |
| mcp__ccd_host__get_storage_usage | ccd_host | 410 |
| mcp__ccd_host__open_in_editor | ccd_host | 610 |
| mcp__ccd_host__request_keep_awake | ccd_host | 622 |
| mcp__ccd_host__reveal_path | ccd_host | 332 |
| mcp__ccd_host__sync_with_base_branch | ccd_host | 1.1k |
| mcp__ccd_pr__bind_pr | ccd_pr | 313 |
| mcp__ccd_pr__get_status | ccd_pr | 243 |
| mcp__ccd_pr__set_auto_merge | ccd_pr | 344 |
| mcp__ccd_pr__set_monitor | ccd_pr | 467 |
| mcp__ccd_pr__unbind_pr | ccd_pr | 190 |
| mcp__ccd_session__dismiss_task | ccd_session | 322 |
| mcp__ccd_session__hand_off_to_session | ccd_session | 344 |
| mcp__ccd_session__list_start_targets | ccd_session | 315 |
| mcp__ccd_session__mark_chapter | ccd_session | 428 |
| mcp__ccd_session__move_to_cloud | ccd_session | 833 |
| mcp__ccd_session__read_widget_context | ccd_session | 181 |
| mcp__ccd_session__start_session | ccd_session | 3.7k |
| mcp__ccd_session_mgmt__archive_session | ccd_session_mgmt | 826 |
| mcp__ccd_session_mgmt__clear_session | ccd_session_mgmt | 501 |
| mcp__ccd_session_mgmt__delete_session | ccd_session_mgmt | 850 |
| mcp__ccd_session_mgmt__detach_session | ccd_session_mgmt | 395 |
| mcp__ccd_session_mgmt__export_transcript | ccd_session_mgmt | 426 |
| mcp__ccd_session_mgmt__get_session | ccd_session_mgmt | 783 |
| mcp__ccd_session_mgmt__get_usage | ccd_session_mgmt | 423 |
| mcp__ccd_session_mgmt__list_events | ccd_session_mgmt | 369 |
| mcp__ccd_session_mgmt__list_sessions | ccd_session_mgmt | 963 |
| mcp__ccd_session_mgmt__search_session_transcripts | ccd_session_mgmt | 319 |
| mcp__ccd_session_mgmt__send_message | ccd_session_mgmt | 512 |
| mcp__ccd_session_mgmt__set_remote_control | ccd_session_mgmt | 450 |
| mcp__ccd_session_mgmt__set_session_effort | ccd_session_mgmt | 360 |
| mcp__ccd_session_mgmt__set_session_fast_mode | ccd_session_mgmt | 440 |
| mcp__ccd_session_mgmt__set_session_model | ccd_session_mgmt | 467 |
| mcp__ccd_session_mgmt__set_session_output_style | ccd_session_mgmt | 560 |
| mcp__ccd_session_mgmt__set_session_permission_mode | ccd_session_mgmt | 503 |
| mcp__ccd_session_mgmt__set_session_title | ccd_session_mgmt | 420 |
| mcp__ccd_session_mgmt__stop_session | ccd_session_mgmt | 401 |
| mcp__ccd_session_mgmt__unarchive_session | ccd_session_mgmt | 420 |
| mcp__ccd_settings__get_settings | ccd_settings | 316 |
| mcp__ccd_settings__set_setting | ccd_settings | 651 |
| mcp__ccd_sidebar__create_group | ccd_sidebar | 196 |
| mcp__ccd_sidebar__create_section | ccd_sidebar | 234 |
| mcp__ccd_sidebar__delete_group | ccd_sidebar | 203 |
| mcp__ccd_sidebar__delete_section | ccd_sidebar | 196 |
| mcp__ccd_sidebar__list_groups | ccd_sidebar | 212 |
| mcp__ccd_sidebar__list_sections | ccd_sidebar | 254 |
| mcp__ccd_sidebar__mark_completed | ccd_sidebar | 241 |
| mcp__ccd_sidebar__move_sessions | ccd_sidebar | 451 |
| mcp__ccd_sidebar__rename_group | ccd_sidebar | 193 |
| mcp__ccd_sidebar__rename_section | ccd_sidebar | 198 |
| mcp__ccd_sidebar__set_pinned | ccd_sidebar | 213 |
| mcp__ccd_sidebar__set_unread | ccd_sidebar | 201 |
| mcp__ccd_sidebar__set_view | ccd_sidebar | 707 |
| mcp__ccd_view__close_pane | ccd_view | 182 |
| mcp__ccd_view__get_layout | ccd_view | 223 |
| mcp__ccd_view__set_transcript_view | ccd_view | 554 |
| mcp__ccd_view__show_pane | ccd_view | 892 |
| mcp__ccd_window__close_split | ccd_window | 220 |
| mcp__ccd_window__get_window_layout | ccd_window | 185 |
| mcp__ccd_window__open_session_in | ccd_window | 601 |
| mcp__ccd_window__set_sidebar_collapsed | ccd_window | 226 |
| mcp__Claude_Browser__browser_batch | Claude_Browser | 839 |
| mcp__Claude_Browser__computer | Claude_Browser | 2k |
| mcp__Claude_Browser__find | Claude_Browser | 256 |
| mcp__Claude_Browser__form_input | Claude_Browser | 379 |
| mcp__Claude_Browser__get_page_text | Claude_Browser | 185 |
| mcp__Claude_Browser__javascript_tool | Claude_Browser | 362 |
| mcp__Claude_Browser__navigate | Claude_Browser | 313 |
| mcp__Claude_Browser__preview_list | Claude_Browser | 94 |
| mcp__Claude_Browser__preview_logs | Claude_Browser | 301 |
| mcp__Claude_Browser__preview_start | Claude_Browser | 688 |
| mcp__Claude_Browser__preview_stop | Claude_Browser | 106 |
| mcp__Claude_Browser__read_console_messages | Claude_Browser | 231 |
| mcp__Claude_Browser__read_network_requests | Claude_Browser | 265 |
| mcp__Claude_Browser__read_page | Claude_Browser | 423 |
| mcp__Claude_Browser__resize_window | Claude_Browser | 623 |
| mcp__Claude_Browser__tabs_close | Claude_Browser | 128 |
| mcp__Claude_Browser__tabs_context | Claude_Browser | 256 |
| mcp__Claude_Browser__tabs_create | Claude_Browser | 216 |
| mcp__Claude_Browser__tabs_select | Claude_Browser | 160 |
| mcp__Claude_Code_iOS_Simulator__build | Claude_Code_iOS_Simulator | 789 |
| mcp__Claude_Code_iOS_Simulator__control | Claude_Code_iOS_Simulator | 2.4k |
| mcp__claude-code-remote__add_repo | claude-code-remote | 1.3k |
| mcp__claude-code-remote__archive_session | claude-code-remote | 194 |
| mcp__claude-code-remote__confirm_repository_trust | claude-code-remote | 645 |
| mcp__claude-code-remote__create_session | claude-code-remote | 1.5k |
| mcp__claude-code-remote__create_trigger | claude-code-remote | 2.4k |
| mcp__claude-code-remote__delete_trigger | claude-code-remote | 510 |
| mcp__claude-code-remote__fire_trigger | claude-code-remote | 460 |
| mcp__claude-code-remote__get_event | claude-code-remote | 184 |
| mcp__claude-code-remote__get_session | claude-code-remote | 472 |
| mcp__claude-code-remote__get_trigger | claude-code-remote | 342 |
| mcp__claude-code-remote__interrupt_session | claude-code-remote | 176 |
| mcp__claude-code-remote__list_computer_folders | claude-code-remote | 872 |
| mcp__claude-code-remote__list_environments | claude-code-remote | 148 |
| mcp__claude-code-remote__list_events | claude-code-remote | 903 |
| mcp__claude-code-remote__list_repos | claude-code-remote | 279 |
| mcp__claude-code-remote__list_sessions | claude-code-remote | 622 |
| mcp__claude-code-remote__list_triggers | claude-code-remote | 1k |
| mcp__claude-code-remote__register_repo_root | claude-code-remote | 325 |
| mcp__claude-code-remote__request_computer_folder | claude-code-remote | 1.1k |
| mcp__claude-code-remote__send_later | claude-code-remote | 886 |
| mcp__claude-code-remote__send_message | claude-code-remote | 1.4k |
| mcp__claude-code-remote__set_session_tags | claude-code-remote | 240 |
| mcp__claude-code-remote__set_session_title | claude-code-remote | 162 |
| mcp__claude-code-remote__subscribe_pr_activity | claude-code-remote | 412 |
| mcp__claude-code-remote__unarchive_session | claude-code-remote | 173 |
| mcp__claude-code-remote__unsubscribe_pr_activity | claude-code-remote | 226 |
| mcp__claude-code-remote__unwatch_url | claude-code-remote | 140 |
| mcp__claude-code-remote__update_trigger | claude-code-remote | 1.8k |
| mcp__claude-code-remote__watch_url | claude-code-remote | 326 |
| mcp__claude-in-chrome__browser_batch | claude-in-chrome | 697 |
| mcp__claude-in-chrome__computer | claude-in-chrome | 2.2k |
| mcp__claude-in-chrome__file_upload | claude-in-chrome | 632 |
| mcp__claude-in-chrome__find | claude-in-chrome | 350 |
| mcp__claude-in-chrome__form_input | claude-in-chrome | 407 |
| mcp__claude-in-chrome__get_page_text | claude-in-chrome | 226 |
| mcp__claude-in-chrome__gif_creator | claude-in-chrome | 920 |
| mcp__claude-in-chrome__javascript_tool | claude-in-chrome | 437 |
| mcp__claude-in-chrome__list_connected_browsers | claude-in-chrome | 229 |
| mcp__claude-in-chrome__navigate | claude-in-chrome | 585 |
| mcp__claude-in-chrome__read_console_messages | claude-in-chrome | 587 |
| mcp__claude-in-chrome__read_network_requests | claude-in-chrome | 504 |
| mcp__claude-in-chrome__read_page | claude-in-chrome | 570 |
| mcp__claude-in-chrome__resize_window | claude-in-chrome | 270 |
| mcp__claude-in-chrome__select_browser | claude-in-chrome | 172 |
| mcp__claude-in-chrome__shortcuts_execute | claude-in-chrome | 320 |
| mcp__claude-in-chrome__shortcuts_list | claude-in-chrome | 215 |
| mcp__claude-in-chrome__switch_browser | claude-in-chrome | 201 |
| mcp__claude-in-chrome__tabs_close_mcp | claude-in-chrome | 232 |
| mcp__claude-in-chrome__tabs_context_mcp | claude-in-chrome | 306 |
| mcp__claude-in-chrome__tabs_create_mcp | claude-in-chrome | 218 |
| mcp__claude-in-chrome__upload_image | claude-in-chrome | 681 |
| mcp__computer-use__app_ax_find | computer-use | 719 |
| mcp__computer-use__app_batch | computer-use | 2.1k |
| mcp__computer-use__app_bring_to_current_space | computer-use | 488 |
| mcp__computer-use__app_click | computer-use | 1.6k |
| mcp__computer-use__app_drag | computer-use | 1.3k |
| mcp__computer-use__app_focus | computer-use | 1.1k |
| mcp__computer-use__app_key | computer-use | 1.2k |
| mcp__computer-use__app_list_windows | computer-use | 488 |
| mcp__computer-use__app_menu | computer-use | 907 |
| mcp__computer-use__app_release | computer-use | 287 |
| mcp__computer-use__app_screenshot | computer-use | 853 |
| mcp__computer-use__app_scroll | computer-use | 778 |
| mcp__computer-use__app_type | computer-use | 1.9k |
| mcp__computer-use__app_zoom | computer-use | 842 |
| mcp__computer-use__computer_batch | computer-use | 1.6k |
| mcp__computer-use__list_apps | computer-use | 313 |
| mcp__computer-use__list_granted_applications | computer-use | 109 |
| mcp__computer-use__open_application | computer-use | 238 |
| mcp__computer-use__read_clipboard | computer-use | 159 |
| mcp__computer-use__release_full_control | computer-use | 184 |
| mcp__computer-use__request_access | computer-use | 1.1k |
| mcp__computer-use__request_full_control | computer-use | 250 |
| mcp__computer-use__request_teach_access | computer-use | 939 |
| mcp__computer-use__switch_display | computer-use | 275 |
| mcp__computer-use__teach_batch | computer-use | 1.6k |
| mcp__computer-use__teach_step | computer-use | 1.4k |
| mcp__computer-use__write_clipboard | computer-use | 171 |
| mcp__Control_Chrome__close_tab | Control_Chrome | 98 |
| mcp__Control_Chrome__execute_javascript | Control_Chrome | 128 |
| mcp__Control_Chrome__get_current_tab | Control_Chrome | 76 |
| mcp__Control_Chrome__get_page_content | Control_Chrome | 97 |
| mcp__Control_Chrome__go_back | Control_Chrome | 90 |
| mcp__Control_Chrome__go_forward | Control_Chrome | 93 |
| mcp__Control_Chrome__list_tabs | Control_Chrome | 98 |
| mcp__Control_Chrome__open_url | Control_Chrome | 121 |
| mcp__Control_Chrome__reload_tab | Control_Chrome | 88 |
| mcp__Control_Chrome__switch_to_tab | Control_Chrome | 103 |
| mcp__e2e88e5c-81e9-422e-b4bc-800faef15728__create_flags_project_connection | e2e88e5c-81e9-422e-b4bc-800faef15728 | 520 |
| mcp__e2e88e5c-81e9-422e-b4bc-800faef15728__get_flags_project_disconnection_link | e2e88e5c-81e9-422e-b4bc-800faef15728 | 338 |
| mcp__e2e88e5c-81e9-422e-b4bc-800faef15728__list_flags_project_connections | e2e88e5c-81e9-422e-b4bc-800faef15728 | 391 |
| mcp__mcp-registry__list_connectors | mcp-registry | 191 |
| mcp__mcp-registry__search_mcp_registry | mcp-registry | 387 |
| mcp__mcp-registry__suggest_connectors | mcp-registry | 526 |
| mcp__scheduled-tasks__create_scheduled_task | scheduled-tasks | 1.5k |
| mcp__scheduled-tasks__delete_scheduled_task | scheduled-tasks | 229 |
| mcp__scheduled-tasks__list_scheduled_tasks | scheduled-tasks | 365 |
| mcp__scheduled-tasks__list_task_runs | scheduled-tasks | 353 |
| mcp__scheduled-tasks__run_scheduled_task | scheduled-tasks | 390 |
| mcp__scheduled-tasks__update_scheduled_task | scheduled-tasks | 925 |
| mcp__terminal__list_terminal_tabs | terminal | 140 |
| mcp__terminal__open_terminal_tab | terminal | 422 |
| mcp__terminal__read_terminal | terminal | 397 |
| mcp__terminal__run_in_terminal | terminal | 1.8k |
| mcp__terminal__stop_terminal_tab | terminal | 462 |
| mcp__visualize__read_me | visualize | 381 |
| mcp__visualize__show_widget | visualize | 1.1k |

### Custom Agents

| Agent Type | Source | Tokens |
|------------|--------|--------|
| harden-issues-attacker | User | 83 |
| harden-issues-seam | User | 77 |
| panel-review-gate | User | 86 |
| panel-review-persona | User | 74 |
| parallel-hunt-claim-gate | User | 78 |
| parallel-hunt-finder | User | 70 |
| parallel-hunt-fix-gate | User | 102 |
| parallel-hunt-fix-gate-critical | User | 96 |
| parallel-hunt-fixer | User | 65 |
| promotion | User | 92 |
| run-issues-finale | User | 80 |
| run-issues-implementer | User | 71 |
| run-issues-implementer-escalated | User | 74 |
| run-issues-review-gate | User | 81 |
| run-issues-review-gate-critical | User | 91 |
| run-issues-verify-gate | User | 67 |

### Skills

| Skill | Source | Tokens |
|-------|--------|--------|
| codebase-design | User | ~100 |
| coderules | User | ~110 |
| daily-brief | User | ~80 |
| designrules | User | ~80 |
| diagnosing-bugs | User | ~60 |
| domain-modeling | User | ~80 |
| grilling | User | ~60 |
| harden-issues | User | ~150 |
| parallel-hunt | User | ~160 |
| prototype | User | ~60 |
| questionrules | User | ~130 |
| research | User | ~80 |
| resolving-merge-conflicts | User | ~30 |
| run-compare | User | ~130 |
| run-issues | User | ~190 |
| site-checks | User | ~120 |
| tdd | User | ~50 |
| wizard | User | ~110 |
| writing-for-agents | User | ~40 |
| writingrules | User | ~180 |
| cowork-plugin-management:cowork-plugin-customizer | Plugin (cowork-plugin-management) | ~110 |
| cowork-plugin-management:create-cowork-plugin | Plugin (cowork-plugin-management) | ~130 |
| engineering:architecture | Plugin (engineering) | ~100 |
| engineering:code-review | Plugin (engineering) | ~90 |
| engineering:debug | Plugin (engineering) | ~90 |
| engineering:deploy-checklist | Plugin (engineering) | ~90 |
| engineering:documentation | Plugin (engineering) | ~100 |
| engineering:incident-response | Plugin (engineering) | ~100 |
| engineering:standup | Plugin (engineering) | ~90 |
| engineering:system-design | Plugin (engineering) | ~90 |
| engineering:tech-debt | Plugin (engineering) | ~90 |
| engineering:testing-strategy | Plugin (engineering) | ~90 |
| anthropic-skills:algorithmic-art | Plugin (anthropic-skills) | ~120 |
| anthropic-skills:brand-guidelines | Plugin (anthropic-skills) | ~90 |
| anthropic-skills:built-in-browser | Plugin (anthropic-skills) | ~290 |
| anthropic-skills:canvas-design | Plugin (anthropic-skills) | ~110 |
| anthropic-skills:chrome-browser | Plugin (anthropic-skills) | ~260 |
| anthropic-skills:computer-use | Plugin (anthropic-skills) | ~320 |
| anthropic-skills:consolidate-memory | Plugin (anthropic-skills) | ~40 |
| anthropic-skills:deep-research | Plugin (anthropic-skills) | ~200 |
| anthropic-skills:doc-coauthoring | Plugin (anthropic-skills) | ~160 |
| anthropic-skills:docs | Plugin (anthropic-skills) | ~340 |
| anthropic-skills:docx | Plugin (anthropic-skills) | ~320 |
| anthropic-skills:explain-usage | Plugin (anthropic-skills) | ~80 |
| anthropic-skills:google-workspace | Plugin (anthropic-skills) | ~330 |
| anthropic-skills:import-memory | Plugin (anthropic-skills) | ~60 |
| anthropic-skills:internal-comms | Plugin (anthropic-skills) | ~120 |
| anthropic-skills:knowledge-base-health-check | Plugin (anthropic-skills) | ~320 |
| anthropic-skills:learn | Plugin (anthropic-skills) | ~340 |
| anthropic-skills:mcp-builder | Plugin (anthropic-skills) | ~100 |
| anthropic-skills:memory-reel | Plugin (anthropic-skills) | ~200 |
| anthropic-skills:morning | Plugin (anthropic-skills) | ~120 |
| anthropic-skills:pdf | Plugin (anthropic-skills) | ~150 |
| anthropic-skills:pptx | Plugin (anthropic-skills) | < 20 |
| anthropic-skills:setup-claude | Plugin (anthropic-skills) | ~40 |
| anthropic-skills:skill-creator | Plugin (anthropic-skills) | < 20 |
| anthropic-skills:slack-gif-creator | Plugin (anthropic-skills) | < 20 |
| anthropic-skills:theme-factory | Plugin (anthropic-skills) | < 20 |
| anthropic-skills:trade-doc-checker | Plugin (anthropic-skills) | < 20 |
| anthropic-skills:web-artifacts-builder | Plugin (anthropic-skills) | < 20 |
| anthropic-skills:xlsx | Plugin (anthropic-skills) | < 20 |
| dataviz | Built-in | ~480 |
| artifact-design | Built-in | ~70 |
| artifact-diagramming | Built-in | ~70 |
| artifact-capabilities | Built-in | ~250 |
| update-config | Built-in | ~240 |
| keybindings-help | Built-in | ~80 |
| code-review | Built-in | ~330 |
| simplify | Built-in | ~60 |
| fewer-permission-prompts | Built-in | ~60 |
| loop | Built-in | ~120 |
| schedule | Built-in | ~130 |
| claude-api | Built-in | ~360 |
| workflow-authoring | Built-in | ~80 |
| run | Built-in | ~120 |
| plugin-authoring | Built-in | ~90 |
| init | Built-in | ~20 |
| security-review | Built-in | ~30 |

## /context on 2026-11-03, second reading (Opus 5.5)

Run in a main session in the Desktop app, working directory `~/code/orderflow`, model claude-opus-5-5, before the first user message. Same day and same directory as the reading above. Two things differ: the model, and the place. Abdul ran the first reading from his phone through a remote session, and this one on the laptop.

**Tokens:** 73.7k / 400k (18%)

### Estimated usage by category

| Category | Tokens | Percentage |
|----------|--------|------------|
| System prompt | 11.2k | 2.8% |
| System tools | 16.2k | 4.1% |
| MCP tools | 16.8k | 4.2% |
| MCP server instructions | 4.6k | 1.1% |
| MCP tools (deferred) | 135.4k | 33.9% |
| System tools (deferred) | 22.6k | 5.6% |
| Custom agents | 1.3k | 0.3% |
| Memory files | 13.5k | 3.4% |
| Skills | 9.9k | 2.5% |
| Messages | 190 | 0.0% |
| Free space | 293.3k | 73.3% |
| Autocompact buffer | 33k | 8.3% |

The per-tool, custom-agent and skill tables are not copied. They list the same rows as the reading above, and the per-tool figures sit within a few tokens of it (spot-checked: the Docs `batch` tool 151 against 150, Context7 `query-docs` 770 against 764, Gmail `create_draft` 1.7k in both).

The gap between the two readings is 19.1k tokens, and 16.4k of it is the loaded "MCP tools" row: 33.2k in the phone session, 16.8k on the laptop. The system prompt row adds 2.2k of the rest.

## /context on 2026-11-03, third reading (laptop, worktree)

Run on the laptop in the Desktop app, in the worktree `~/code/orderflow/.claude/worktrees/staging-deployment-setup-23e03d`, after a short first message (Messages 668). The model is not recorded.

**Tokens:** 76k / 400k (19%)

| Category | Tokens | Percentage |
|----------|--------|------------|
| System prompt | 13k | 3.3% |
| System tools | 16.2k | 4.1% |
| MCP tools | 16.8k | 4.2% |
| MCP server instructions | 4.6k | 1.1% |
| MCP tools (deferred) | 135.4k | 33.9% |
| System tools (deferred) | 22.6k | 5.6% |
| Custom agents | 1.3k | 0.3% |
| Memory files | 13.5k | 3.4% |
| Skills | 9.9k | 2.5% |
| Messages | 668 | 0.2% |
| Free space | 291k | 72.7% |
| Autocompact buffer | 33k | 8.3% |

### Memory files

| Type | Path | Tokens |
|------|------|--------|
| User | ~/.claude/CLAUDE.md | 4.3k |
| Project | ~/code/orderflow/.claude/worktrees/staging-deployment-setup-23e03d/CLAUDE.md | 3.7k |
| AutoMem | ~/.claude/projects/-Users-roufmlp-code-orderflow/memory/MEMORY.md | 5.5k |

### What the three readings show

The phone reading sits 16.8k above this one, and 16.4k of that is the loaded "MCP tools" row (33.2k against 16.8k). Its system prompt row (13.4k) is close to this reading's 13k, so the system prompt is not what the remote session adds. Both laptop readings carry the same 16.8k of loaded MCP tools. The lead is that a remote session from the phone loads about 16k of MCP tools up front that a laptop session defers. Nobody listed which tools those are, so it stays a lead.

The 1.8k system prompt gap between the two laptop readings is not explained; the worktree and the model are the two candidates, and neither was isolated.

The 13.5k of memory files splits 4.3k global `CLAUDE.md`, 3.7k project `CLAUDE.md` and 5.5k `MEMORY.md`. The memory index is the largest of the three.
