Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: grilling
Blocked by: 34

# How every version 2 session stays under 300k tokens

## Question

Abdul wants every version 2 session and agent to stay under 300k tokens of context, 400k at most, because past that size agents make mistakes. "What the interview settles before a run" already keeps the interview small: subagents read the code, and the run starts in a clean session. Nothing yet enforces a limit anywhere else, and the hygiene rules in `CLAUDE.md` only remind.

Decide, from the facts "What Claude Code offers to measure and cap a session's context" finds, what refuses a session or agent that passes the limit, what it does at the limit (stop, save a handoff, compact or start a fresh agent), and how each role in `/build-feature`, the fast lane's build session, the brainstorm session and the evening check is sized to stay under it.

The lighter option: one hook that blocks every tool call except a handoff write once the last turn passes 300k, with the same limit for every role, and roles cut so that version 1's sizes fit. A heavier answer says what this would cost.

Changed by "What Claude Code offers to measure and cap a session's context" (2026-11-01): the lighter option is now one setting, not a hook. `CLAUDE_CODE_AUTO_COMPACT_WINDOW` at about 333k compacts every model and every subagent near 300k, and beats each agent's own setting. Today only Opus 5.5 has a window, of 400k. A hook that stops at 300k can read the size from the transcript, inside subagents too, but compaction cannot stop an agent and a hook cannot compact one, so the choice is between the two or both. A subagent starts at about 90k tokens, which leaves about 210k for its work.

## Answer

One setting holds every session and agent under 400k for now: `CLAUDE_CODE_AUTO_COMPACT_WINDOW=400000`. Each one compacts at about 367k and carries on. No hook stops anything. Abdul accepted this on 2026-11-02, and moved the limit from the 300k first proposed to 400k, because every session starts at about 100k before it reads a thing. A 300k limit would leave a subagent about 200k for its work. The limit drops to 300k once sessions start smaller.

**Why a setting, not a hook.** A hook that blocks tool calls past the limit stops an agent, and then something has to start a fresh one. A stopped workflow agent returns no result, which the run counts as an API failure, and the docs do not say hooks fire in workflow agents at all. The hook would also take one of the plugin's four hook slots. Compaction keeps every role under the limit for one line, and version 1 already compacted 172 times at about 367k under the Opus-only window. A hook as a second stop at 400k was dropped too: compaction already keeps sessions below it.

**One limit for every role.** The env var beats each agent's own window, so a smaller window for one role would mean dropping the env var. One number is one rule.

**Where it lives.** A plugin cannot set an env var; its settings file applies two keys and drops the rest. So the setting goes in three places:

1. `CLAUDE_CODE_AUTO_COMPACT_WINDOW=400000` in Abdul's `~/.claude/settings.json`. It replaces today's `modelSettings.claude-opus-5-5.autoCompactWindow` line, which covers Opus 5.5 alone and let Opus 5 and Sonnet 5.5 agents reach 934k and 776k. The fast-lane build session, the interview, `/build-feature` and the evening check all run on the laptop, so this one line covers them.
2. `autoCompactWindow: 400000` in the frontmatter of every agent file in the plugin, so the build roles compact the same way for anyone who installs it. Their main sessions keep their own window.
3. The env var in the cloud environment the brainstorm routine runs in. A repo's `.claude/settings.json` `env` block is not applied in every cloud session.

**Sizing the roles.** Nothing is cut up front: the size of a change note cannot be measured before it runs, and a file limit would be a guess. In version 1, 20% of implementers and 35% of main sessions passed 300k; under this setting they compact once and carry on. The audit counts compactions per role, and when a role compacts in more than one run in ten it proposes a fix to Abdul. For the implementer that fix is smaller notes. The one session that holds something compaction could lose is the interview, so it writes each of Abdul's answers into `changes/<feature>/plan.md` as he gives it. Every other role starts fresh or reads its state from git.

**Moving to 300k.** The audit's Tokens row shows each role's largest context, its compactions and its median start size. Abdul reads it on the 1st, through the audit file linked from the brainstorm page. When start sizes fall, the audit adds one line to the page asking whether to lower the window to 300k, and Abdul answers yes or no. There is no trigger number; the change is one line in each of the three places. A new research ticket, "What fills a session's first 100k tokens", finds what the start load is made of and what version 2 can cut.

**Context hygiene in `CLAUDE.md`.** The section stays, cut from 21 lines to 8, with all five rules. Abdul approved this text on 2026-11-02:

> **Context hygiene**
> Every turn re-bills the whole context. A setting compacts each session at 400k; these keep sessions well under it.
> - Bulk or repeated work goes to a subagent, Sonnet for mechanical runs, which writes its progress to a file.
> - Before the third repeat of a UI action, look for an API, CLI or script.
> - Read text, not screenshots, unless the answer is visual.
> - When a phase ends, write the handoff and tell me to `/clear`. One issue per session.
> - A handoff serves only the session that resumes the same work. Anything worth keeping goes to a durable home when it is written.

The reminders stay because agents use them to raise context size with Abdul when he decides things, even though the setting does the enforcing.
