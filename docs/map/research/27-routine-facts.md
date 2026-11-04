# Cloud routines (now called "scheduled tasks"): facts from official docs, fetched 2026-11-01

Note: the docs now call routines "cloud scheduled tasks, formerly routines" (https://code.claude.com/docs/en/routines.md, research preview). `/schedule` alias is `/routines`.

## 1. Branch pushes
- Default: "Claude pushes its work to a branch prefixed with `claude/` unless your prompt directs it to push to another branch." So the prefix is a default, not a hard lock. https://code.claude.com/docs/en/routines.md (section "Repositories and branch permissions")
- The same section says: to control which branches a run can push to, use branch protection rules or rulesets on GitHub.
- The GitHub proxy "rejects branch deletions and pushes of anything other than a branch, such as a tag. It doesn't limit which branches a push can update." https://code.claude.com/docs/en/cloud-environments.md#github-proxy
- No setting called "allow unrestricted branch pushes" appears on routines.md, cloud-environments.md, claude-code-on-the-web.md, web-quickstart.md or claude-projects.md (grep found none). The docs do NOT document such a toggle. A push to the default branch is therefore governed by the prompt plus GitHub branch protection, not a per-repo or per-environment switch. (Absence in these pages; not proof it never existed in the UI.)

## 2. Plugins, skills, CLAUDE.md in a cloud session
- Repo `.claude/settings.json` `enabledPlugins` / `extraKnownMarketplaces`: NOT installed. Table row "Plugins and marketplaces declared in your repo's .claude/settings.json: No". https://code.claude.com/docs/en/cloud-environments.md#what-carries-over-from-your-setup
- Reason: "A cloud session doesn't add the marketplaces a repository lists under extraKnownMarketplaces, because that requires the workspace trust dialog, which a cloud session never shows." https://code.claude.com/docs/en/plugins/loading.md
- Repo `.claude/settings.json` hooks and permission rules: yes in a session with ONE repository; with several repos only `enabledPlugins` and `extraKnownMarketplaces` are read (and those still do not load). https://code.claude.com/docs/en/settings.md#settings-in-cloud-sessions
- Repo `.claude/skills/`, `.claude/agents/`, `.claude/commands/`, `.claude/rules/`, and `CLAUDE.md`: yes (part of the clone). cloud-environments.md#what-carries-over-from-your-setup. Routines page confirms: "those skills include the ones committed to the cloned repository" (routines.md).
- `~/.claude/skills/` and user `~/.claude/CLAUDE.md`: not available. Skills enabled on your claude.ai account load automatically. https://code.claude.com/docs/en/skills.md (section "Use skills in Cowork and cloud sessions")
- Plugin from a public GitHub marketplace, or a private one: the docs do NOT answer. Documented routes found: plugins enabled on the claude.ai account ("synced") load in Cowork and terminal sessions (plugins/loading.md "Plugins synced from claude.ai"); the docs do not say they load in cloud scheduled-task runs. For projects only, "Project settings > Plugins" loads plugins into cloud threads (claude-projects.md). Nothing on private marketplaces in cloud.
- Workaround NOT documented: a setup script could try `claude plugin install`; docs do not say this works.

## 3. Setup scripts / environments / multiple repos
- Yes. "A setup script is a Bash script that runs when a new cloud session starts, before Claude Code launches... Scripts run as root on Ubuntu 24.04." Must exit zero, finish in about 5 min to be cached, env vars not yet set when it runs; up to 64 KB. Set in the environment dialog. https://code.claude.com/docs/en/cloud-environments.md#setup-scripts
- A task uses one environment (routines.md "Select an environment"; "Environments and network access").
- Multiple repos: yes. "select one or more GitHub repositories"; "Each repository you add is cloned on every run" (routines.md). Created branches are `claude/`-prefixed for each.
- Cloning a second repo inside a setup script: docs do not say. Relevant facts: GitHub proxy serves API requests only for repos attached to the session; others get 403 "GitHub access to ... is not enabled for this session" (cloud-environments.md#github-proxy). Simplest documented route is to attach both repos to the task.
- Caveat: with several repos, hooks (SessionStart) from repo settings do not run; use a setup script. cloud-environments.md "Limitations in cloud sessions".

## 4. Notification
- Official routines.md and cloud-environments.md contain no mention of notifications for finished runs (grep for "notif" found none). The docs do NOT answer this.
- Related, not the same: mobile push notifications exist for Remote Control sessions only, with two on/off toggles and "no per-event configuration" (https://code.claude.com/docs/en/remote-control.md#mobile-push-notifications). Projects send desktop notifications (claude-projects.md). Neither is stated to cover scheduled-task runs.
- Third-party only (not official): a GitHub issue claims routine push/email notifications exist but did not deliver: https://claudeissues.com/issue/80880-bug-scheduled-routine-notifications-push-email-not-delivered-despite-correct-set
- Runs can be opened from the task detail page at claude.ai/code/routines (routines.md "View and interact with runs").

## 5. Schedule
- `0 9 1,15 * *`: docs do NOT say whether comma lists in day-of-month are accepted. Only documented: custom cron is entered via the **Custom** option in the task's edit dialog or `/schedule update`; example `0 */2 * * *`. https://code.claude.com/docs/en/routines.md#add-a-schedule-trigger
- Hours in a plain five-field expression are UTC ("`0 9 * * 1-5` runs at 9:00 AM UTC"); a `CRON_TZ=` prefix is allowed.
- Minimum interval: "Expressions that run more often than once per hour are rejected." Runs exactly on the hour can start several minutes late.
- Limits: scheduled runs 100 per hour per account (run waits); Run now/API/one-off re-run 30 per hour per task. No per-day cap stated. routines.md#usage-and-limits. Runs also draw on subscription usage.
- One-off runs are supported ("/schedule tomorrow at 9am ...").

## 6. GitHub write access and the Claude GitHub app
- Access comes from either the Claude GitHub App or `/web-setup` (sends local `gh` token). "Any repository your gh token can access, whether or not the Claude GitHub App is installed." https://code.claude.com/docs/en/claude-code-on-the-web.md#github-authentication-options
- So for a routine that only clones and pushes, the app is not required if `/web-setup` is used. With the browser/App route, private repos need the app installed on them (web-quickstart.md).
- The app IS required for GitHub triggers: "The Claude GitHub App must be installed on the repository you want to subscribe to"; `/web-setup` "does not install the Claude GitHub App" (routines.md "Add a GitHub trigger"). Also needed for Auto-fix and Projects.
- Push/commit identity is you: "Commits and pull requests carry your GitHub user" (routines.md). GitHub credentials stay in a proxy outside the VM.
- If the GitHub connection expires, runs are skipped for up to 72 hours, then the task turns off (routines.md).
- Organization IP allowlist breaks Anthropic-hosted scheduled tasks (claude-code-on-the-web.md "Limitations").
