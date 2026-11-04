# What recent Claude Code features and Anthropic posts can replace

Research for ticket 13 of the workflow-v2 map. Checked on 2026-10-27 against Claude Code 2.1.311.

Most of the chain now has a built-in twin. Dynamic workflows do what run-issues and parallel-hunt do by hand, and `/code-review`, `/verify` and `/goal` cover the gates and the keep-going loop. What stays custom is Abdul's own rules, such as risk-path routing and the push ban. Most of the plumbing beneath them can go.

Dates are the npm publish date of the version named. CL means the [changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md).

| Feature or practice | What it does | Could replace or shrink | Effort | Source |
|---|---|---|---|---|
| Dynamic workflows, `ultracode`, saved `/<name>` workflows | Claude writes a JS script that runs up to 1,000 agents, 16 at a time by default. The script holds the loop and results. Runs resume, pause at a usage limit, and save as commands. No user input mid-run | run-issues runner and ledger, parallel-hunt round, harden-issues fan-out; hooks `run-issues-foreground-gate`, `-parallel-gates`, `-wakeup-gate`, `-brief-cap` | Large | CL 2.1.154 (2026-05-28), 2.1.271; [workflows](https://code.claude.com/docs/en/workflows) |
| `/code-review [effort] [--fix]`, `ultra` | A background reviewer at low to max effort. `ultra` runs a multi-agent review in the cloud that verifies its findings; `claude ultrareview` runs it from a script. It follows CLAUDE.md | run-issues review gates and finale, parallel-hunt fix gates | Small | CL 2.1.111 (2026-04-16), 2.1.147, 2.1.288; [code-review-local](https://code.claude.com/docs/en/code-review-local), [ultrareview](https://code.claude.com/docs/en/ultrareview) |
| `/verify`, `/run`, `/run-skill-generator` | Bundled skills that build the app, run it and watch the result rather than trusting tests | run-issues verify gate | Small | [commands](https://code.claude.com/docs/en/commands). Release date not confirmed |
| `/goal <condition>` | After each turn a small model checks the condition and starts another turn until it holds. Works with `-p`. It is a session-scoped prompt Stop hook | One-issue implement loop; the fast lane's "keep going until green" | Small | CL 2.1.139 (2026-05-11); [goal](https://code.claude.com/docs/en/goal) |
| Auto mode as default, `/auto-mode-setup`, `autoMode.hard_deny` | A classifier approves or blocks each action: 0.4% false positives, 17% false negatives on overeager actions. Default for new sessions | Prompt-avoidance in the Bash guards. True "never" rules stay as deny rules or hooks, per the docs | Small | CL 2.1.136, 2.1.284 (2026-09-28), 2.1.304; [auto mode post](https://www.anthropic.com/engineering/claude-code-auto-mode) (2026-03-25) |
| Hook hygiene: `onFailure: "block"`, exec-form `args` | A failing hook now blocks instead of letting the call through. The docs say that at "forty of them, most are probably preferences" | The 34 hook entries in `~/.claude/settings.json`: audit and cut | Medium | CL 2.1.295 (2026-10-08); [best-practices](https://code.claude.com/docs/en/best-practices) |
| Model pinning: `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, `CLAUDE_CODE_WORKFLOW_SUBAGENT_MODEL`, `Agent(model:opus)` rules | Forces or denies subagent models through settings | `model-map-gate`, `model-landed-check` | Small | CL 2.1.178, 2.1.257, 2.1.296 |
| Continue at usage limit | The session resumes by itself when the limit resets. Only for interactive subscription sessions, resets within 24 hours, at most two waits per workflow run | run-issues "resume across usage limits" | Small | CL 2.1.234 (2026-08-17), 2.1.271 |
| Agent view, `--bg`, `/fork`, `/subtask`, `worktree.baseRef` | One screen for background sessions, each in its own worktree. Sessions can message each other | `worktree-base-drift`, `worktree-snapshot-notice`, the handoff skill for parallel work | Medium | CL 2.1.133, 2.1.139, 2.1.224; [agents](https://code.claude.com/docs/en/agents) |
| Scheduled tasks (`/schedule`, desktop tasks, `/loop`) | Cloud runs on a cron, an API call or a GitHub event, and push to `claude/` branches | daily-brief build, a nightly hunt. Cloud pushes clash with "push is mine"; ticket 05 decides | Small to medium | CL 2.1.71; [routines](https://code.claude.com/docs/en/routines) |
| Monitor tool; long foreground sleeps blocked | Streams events from a background script instead of sleeping | `fixed-sleep-guard` | Small | CL 2.1.98 (2026-04-09), 2.1.310. When the block reached first-party installs is not confirmed |
| `/batch` | Splits one large change into 5 to 30 worktree-isolated subagents after you approve a plan | run-issues for mechanical sweeps | Small | CL 2.1.63; [commands](https://code.claude.com/docs/en/commands) |
| Plugins: `claude plugin install --marketplace`, `claude plugin eval`, plugin `workflows/`, `/skill-doctor`, `/doctor prompt-audit` | One install command, scored plugin evals, reports on unused skills and stale prompts | The scrub-and-sync step, the install path (ticket 10), skill pruning | Medium | CL 2.1.261, 2.1.269, 2.1.283, 2.1.292; [plugin-evals](https://code.claude.com/docs/en/plugin-evals) |
| Mods | JS handlers that can refuse or rewrite tool calls and agent spawns | Could hold the guards, but a mod can approve a call a `PreToolUse` hook blocked. Not recommended | Large | CL 2.1.287 (2026-10-01); [mods](https://code.claude.com/docs/en/plugins/mods/overview) |
| Practice: start simple, add scaffolding only on failure | Anthropic's planner, generator and evaluator harness dropped its sprints when Opus 4.6 arrived. Rule: "find the simplest solution possible" | Supports the fast lane: one agent plus one end-of-work evaluator | None | [harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps) (2026-03-24) |
| Practice: no orchestrator, tests as oracle | 16 parallel Claudes claimed tasks with lock files in git and no coordinator. Near-perfect tests did the steering | The parallel-hunt shape: lighter coordination, heavier checks | None | [C compiler](https://www.anthropic.com/engineering/building-c-compiler) (2026-02-05) |

## The five changes with the biggest likely speed gain

1. Rebuild run-issues as one saved dynamic workflow (implement, `/code-review`, `/verify` per issue). Resume, the usage-limit pause and fan-out come built in, and half the run-issues hooks go with the ledger.
2. Swap the custom review gates and finale for `/code-review high --fix`, and keep `ultra` for money and auth diffs.
3. Run the fast lane as one session in auto mode with `/goal "tests pass and /verify is green"`. No issue files, no chain.
4. Cut the 34 hook entries to the few true "never" rules. Move those into `autoMode.hard_deny` or deny rules with `onFailure: "block"`, and delete the hooks that only enforce preferences.
5. Ship the skills as one plugin from one marketplace and guard it with `claude plugin eval`. That ends the scrub-and-sync step.

## Not confirmed

- First-hand 2026 posts by Claude Code staff such as Boris Cherny sit on X, which I could not fetch. Only secondary write-ups turned up, so none is cited.
- The release dates of `/verify` and `/run`, and when long foreground sleeps were first blocked.
- The speed gains are judgement. No run-compare record backs them yet.
