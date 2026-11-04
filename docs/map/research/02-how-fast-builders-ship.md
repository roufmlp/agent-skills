# How fast builders ship with Claude Code

Researched 2026-10-27 for ticket 02. Sources: Anthropic docs and engineering posts, plus first-hand builder write-ups. Unverified items are marked **unconfirmed**.

## Steps fast builders use

1. **Write a spec, or have Claude interview you for one.** Anthropic's advice: ask Claude to interview you, write `SPEC.md`, then start a fresh session to build from it, so the build has "a written definition of done". [Best practices](https://code.claude.com/docs/en/best-practices)
2. **Plan first only when the change is not obvious.** Plan mode proposes a plan and makes no edits until you approve. [Common workflows](https://code.claude.com/docs/en/common-workflows)
3. **Give Claude a check it can run**: a test, build exit code, linter, fixture diff, or browser screenshot. Put the command in `CLAUDE.md`. [Best practices](https://code.claude.com/docs/en/best-practices)
4. **Build in small units, one feature at a time.** Anthropic's long-running-app harness starts with a progress file and a JSON feature list (200+ items, all failing), then ships one feature per session with a commit and a note. [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
5. **Let it run unattended once five questions have answers**: what done looks like, how it checks itself, what it may touch, what stops it (`--max-turns`, `--max-budget-usd`), who signs off. [Best practices](https://code.claude.com/docs/en/best-practices)
6. **Review the result, then deploy.** One builder reviewed PR descriptions, especially their "What's NOT in this PR" sections, and wrote prompts like incident reports. [Towards AI write-up](https://towardsai.com/p/machine-learning/i-built-an-app-entirely-with-claude-code-this-is-what-i-learnt)

## What they skip

- **Context fiddling.** Anthropic now lists as droppable: aggressive context management, emphatic CAPS in `CLAUDE.md`, and "keep going" nudges. [Best practices](https://code.claude.com/docs/en/best-practices)
- **Per-action approvals.** New sessions start in auto mode, where a classifier reviews risky actions. [Best practices](https://code.claude.com/docs/en/best-practices)
- **Reading the code.** Anthropic teams accepted output "with minimal human review", and data scientists built visualisations "without understanding the code themselves". [How Anthropic teams use Claude Code](https://claude.com/blog/how-anthropic-teams-use-claude-code) The Towards AI builder also read little code and expects higher upkeep cost.
- **Early tests and a `CLAUDE.md`.** The same builder regrets adding both late (week three), and regrets starting single-tenant, the largest source of rework (rework was 6.5% of tokens).

## How they check the result

- Tests, typecheck, linter. A `Stop` hook makes the harness refuse to end the turn until the check passes. [Best practices](https://code.claude.com/docs/en/best-practices)
- `/code-review` in a fresh subagent that never saw the conversation. [Best practices](https://code.claude.com/docs/en/best-practices)
- `/verify`: Claude builds and runs the app. The docs say this catches what tests and typecheck miss. [Best practices](https://code.claude.com/docs/en/best-practices)
- Browser automation acting as a user; unit tests and `curl` alone missed end-to-end bugs. [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Ask for evidence (command and output), not "all tests pass". [Best practices](https://code.claude.com/docs/en/best-practices)
- Warning from the compiler project: the verifier must be near-perfect or the agent solves the wrong problem, and passing tests is not proof of completion. [Building a C compiler](https://www.anthropic.com/engineering/building-c-compiler)

## Measured times

- One solo builder, one app: 26 calendar days, 97 active hours, 9.9 billion tokens, own attention about a quarter to a third of that. Self-reported, one app, no dollar cost. [Towards AI](https://towardsai.com/p/machine-learning/i-built-an-app-entirely-with-claude-code-this-is-what-i-learnt) Author name **unconfirmed**; read through a summarising fetch.
- Anthropic's C compiler: about 2,000 sessions, two weeks, 16 agents, just under $20,000. A research stunt, not a solo-builder rate. [Building a C compiler](https://www.anthropic.com/engineering/building-c-compiler)
- Anthropic team anecdotes: research from an hour to 10-20 minutes. Self-reported, small tasks. [Same blog](https://claude.com/blog/how-anthropic-teams-use-claude-code)
- I found no primary, measured idea-to-deploy time for a product holding customer data.

## Fit for an app with real customer data

| Approach | Fits | Fails |
|---|---|---|
| Spec, then fresh-session build | Any app. | A spec forces no data rules unless you write them. |
| Auto mode and unread code | Throwaway prototypes, internal tools. | Anthropic reports a 17% miss rate on real overeager actions and calls auto mode "not a drop-in replacement for careful human review" on high-stakes infrastructure; in-project file edits skip the classifier. [Auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode) |
| Tests, typecheck, `Stop` hook | Fast, enforced, always worth keeping. | Only catch what someone wrote a test for. |
| Fresh-agent review against the spec | Catches missed requirements without Abdul reading code. | Reviewer shares the model's blind spots. Strength on security flaws is **unconfirmed**. |
| Browser end-to-end check | Proves the real flow works. | Misses native browser dialogs. [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) |
| Parallel agents | Many independent tasks. | One tangled task does not split; regressions need CI. |

Simon Willison separates "vibe coding" from engineering you can maintain, and relies on tests, review and previews before release. [Vibe engineering](https://simonwillison.net/2025/Oct/7/vibe-engineering/)

**Unconfirmed:** Boris Cherny's reported habits (plan mode first, parallel sessions). Only secondary write-ups found; not relied on.

## Implications for a fast lane

1. **The entry ticket is one page: a spec with a "done" check the agent can run.** Interview, then `SPEC.md`, then a fresh build session. No issue files.
2. **Checks are mechanical, not read.** Tests, typecheck, one browser pass and a `Stop` hook, with the evidence printed. Abdul reads the evidence and the running product.
3. **One fresh-context review against the spec**, told to skip style. It replaces the multi-gate chain.
4. **Cap every unattended run** with turns and budget. The merge stays the single human sign-off.
5. **The fast lane holds no customer data and no money, auth or secrets.** Auto mode's miss rate and unread code rule that out. Set tenancy and tests on day one: the one measured solo build lost most time retrofitting them.
