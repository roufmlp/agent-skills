# Scheduling a Claude Code session (research 05)

Checked 2026-10-27 on code.claude.com. "Unconfirmed" means the docs do not say.

## 1. Cloud scheduled tasks (routines, `/schedule`)

Source: https://code.claude.com/docs/en/routines.md

- **Schedule.** Presets: hourly, daily, weekly. **Custom** takes a cron expression (edit dialog or `/schedule update`), read in UTC unless it starts with `CRON_TZ=`. Monthly is `0 9 1 * *`. A strict every-14-days run cannot be written in cron; `0 9 1,15 * *` is the nearest. That the field accepts `1,15` is unconfirmed; `/loop` documents comma lists (https://code.claude.com/docs/en/scheduled-tasks).
- **Cost.** Pro, Max, Team, Enterprise. Runs draw normal subscription usage; no separate fee.- **Interactive?** Autonomous, in auto mode. A run waits only on certain prompts, which Abdul answers by opening the run. Every run is a full session he can open and continue.
- **Output.** Run history at claude.ai/code/routines; `claude/` branches and PRs; a claude.ai artifact (private until shared); connectors such as Slack. Email is unconfirmed. A push notice for a finished run is unconfirmed; the mobile docs tie push to Remote Control (https://code.claude.com/docs/en/mobile.md).
- **Laptop.** Not needed; it runs on Anthropic cloud.
- **Limits.** Fresh clone of a GitHub repository, so no local files. Research preview.- **Setup.** In a CLI logged in with a claude.ai account, run `/schedule` and answer the questions. Or open claude.ai/code/routines and click **New task**. A Console API key login hides `/schedule`.

## 2. Desktop app scheduled tasks (local)

Source: https://code.claude.com/docs/en/desktop-scheduled-tasks.md

- **Schedule.** Hourly, Daily, Weekdays, Weekly, Manual, Custom (cron in local time, numeric weekdays). Monthly is `0 9 1 * *`. No strict two-weekly option.
- **Cost.** Subscription usage. A plan restriction is unconfirmed.
- **Interactive?** Each run is a fresh session with a per-task permission mode. In Manual mode a run stalls until Abdul answers the prompt in that session.
- **Output.** Local files and git in the chosen folder, plus the session under History. A notice when a normal run ends is unconfirmed.
- **Laptop.** Must be awake with the app open. A run missed during sleep is skipped; on wake one catch-up run fires for the latest missed time (within seven days). A **Keep computer awake** setting exists; closing the lid still sleeps.
- **Setup.** Code tab, **Scheduled**, **New task**, turn on **Only on this computer**, pick a folder and a schedule, **Create**. Needs Desktop 1.1.5368 or later.

## 3. Local cron running `claude -p`

Sources: https://code.claude.com/docs/en/headless.md and https://code.claude.com/docs/en/authentication

- **Schedule.** Cron or launchd, outside Claude, so any pattern. A strict every-14-days run needs a small guard script of our own.
- **Cost.** Subscription, if authenticated with `claude setup-token` (a one-year token in `CLAUDE_CODE_OAUTH_TOKEN`; Pro, Max, Team or Enterprise). `--bare` ignores that token and needs an API key, which bills per token.
- **Interactive?** One-shot: `-p` runs once and exits. Calls needing approval are denied. A later `claude -p --resume <session_id>` can continue the same conversation.
- **Output.** Whatever the shell does: a file, `--output-format json`, `mail`, a git commit. We script it. The setup token cannot fetch claude.ai connectors.
- **Laptop.** Must be awake at fire time. Catch-up of missed runs is unconfirmed.
- **Setup.** `claude setup-token`; put the token in the cron environment; write a wrapper script; add a crontab line.

## Comparison

Only the cloud task runs with the laptop shut. It needs no script and no token, and each run is a session Abdul can open and answer. Its weak points are the fresh GitHub clone and the unconfirmed email and push notice. Desktop tasks reach local files and can wait on prompts, but skip runs while the laptop sleeps. Local cron is the most flexible and the most work: we write the wrapper and the email, and nothing waits for him because `-p` exits.

**Simplest option for a brainstorm every two to four weeks that prepares ideas, then waits:** a cloud scheduled task on `0 9 1 * *` (monthly), or `0 9 1,15 * *` (about two-weekly). The run prepares the ideas, and Abdul opens that session from claude.ai/code/routines and continues it. Test once whether a run sends him any notice.
