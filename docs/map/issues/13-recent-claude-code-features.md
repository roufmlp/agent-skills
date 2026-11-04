Status: resolved
Type: research

# What recent Claude Code features and Anthropic posts can replace

## Question

Which Claude Code features released in 2026, and which recent posts by Anthropic and its staff, could replace parts of Abdul's custom machinery or make building faster? Look at the Claude Code changelog and release notes, the official docs, the Anthropic engineering blog and posts by Anthropic employees on how they use Claude Code themselves. For each feature or practice, say what it does, which of Abdul's skills or hooks it could replace or shrink (see "What each skill and hook does today"), and how much effort adopting it would take. "How fast solo builders ship with Claude Code today" covers outside builders; this ticket covers what Anthropic ships and says.

## Answer

Claude Code now ships much of what Abdul built by hand. The five changes with the largest likely gain, in the agent's judgement (no run record measures them yet):

1. run-issues becomes one saved workflow (implement, `/code-review`, `/verify` per issue). Workflows already resume, wait out the usage limit and run agents in parallel, so the ledger and about half the run-issues hooks go.
2. `/code-review high --fix` replaces the custom review gates and the finale. `ultra` stays for money and auth diffs.
3. The fast lane is one session in auto mode with `/goal "tests pass and /verify is green"`. No issue files, no chain.
4. The 34 hook entries shrink to the few true "never" rules, moved into `autoMode.hard_deny` or deny rules. The best-practices page says that at around forty hooks, most are preferences.
5. The skills ship as one plugin from one marketplace, tested with `claude plugin eval`. That removes the scrub-and-sync step.

Built-in model pinning could replace `model-map-gate` and `model-landed-check`, and the Monitor tool could replace `fixed-sleep-guard`. Mods are not a safe home for guards: without managed settings, a mod can approve a call a PreToolUse hook blocked. Posts by Claude Code staff on X could not be fetched, so none is cited.

Findings: `.scratch/workflow-v2/research/13-recent-claude-code-features.md` on branch `research/recent-claude-code-features`.
