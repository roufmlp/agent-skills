# Allow rules for a build-feature run

The build agents run in auto mode, where the classifier reviews every tool call it has no rule for and a blocked call stops the note. These rules go in the global `~/.claude/settings.json` under `permissions.allow`, so they hold in every product repo; Abdul approves the edit in the settings prompt. The product's own `.claude/settings.json` keeps the read-only commands (`cat`, `ls`, `grep`, the test runners) as Orderflow's already does. The first long run is the place to add what still prompts.

Written 2026-11-03 (stage two, session 5). The switch moves this file into the plugin beside the workflow.

## The session that starts the run

| Rule | Why |
| --- | --- |
| `Read(~/.claude/skills/**)` | The Workflow tool starts a script only from a file the session may read, and the script lives in the skills repo while the session's folder is the product repo; the roles also read `templates/` and `CONTEXT.md` there. |
| `Workflow` | The launch of `build-feature-run`, and the restart after a stop, without a prompt. In auto mode the first launch records consent once; this rule covers `claude -p` and a background session too. |
| `Bash(python3 ~/.claude/skills/workflow/lib/*)` | `plan_check.py`, `feature_run.py`, `suite.py`, `note_check.py`, `side_by_side.py`: the scripts every role and the session call. |
| `mcp__ccd_host__request_keep_awake` | Keep-awake for the run's hours. |
| `PushNotification` | The phone notice at the end and from the watchdog. |
| `ScheduleWakeup` | The 30-minute watchdog. |
| `TaskStop` | The watchdog stops a run that has written nothing in 30 minutes before it starts the run again. |

## The build agents

| Rule | Why |
| --- | --- |
| `Bash(git:*)` | Every role: `git -C <tree> worktree add`, `merge`, `merge-base`, `mv`, `revert`, `commit --pathspec-from-file`, `log`, `diff`, `show`, `status`. The `-C <tree>` form means a per-subcommand rule cannot be written. The git hooks and `git-shared-state-guard.py` refuse the forms that break shared state, and no role pushes; see the deny rule below. |
| `Bash(node:*)` | `node scripts/run-db.mjs claim`, the product's own scripts. |
| `Bash(npm:*)` | `npm run typecheck`, `npm test`, `npm run e2e`, `npm audit`, `npm run build` through `suite.py` and the done checks. |
| `Bash(npx:*)` | `npx vitest`, `npx playwright test`, `npx tsc`, `npx next build`. |
| `Bash(cp:*)` | The note worktree's `node_modules` clone and `.env.local` copy; the final verifier's baseline copies for the side-by-side page. |
| `Bash(mkdir:*)` | Report and baseline folders. |
| `Bash(psql:*)` | Gate step 1, the `pg_tables` query for RLS, and step 3's minted sessions. |
| `Bash(curl:*)` | Gate steps 3, 4, 6 and 7: the other user's rows, the unsigned webhook call, the error pages, the rate limit's count plus one. |
| `Edit(~/code/**)` | The implementer's and note checker's edits in a product tree; every product lives under `~/code`. |
| `Write(~/code/**)` | The implementer's new files, every role's report, the verifier's throwaway walk spec, the side-by-side page. |
| `Edit(~/.claude/pending.md)` | A "Decide" entry from an implementer or the note checker. |
| `Write(~/code/*/.git/build-feature/**)` | The reject reports, inside the git common dir so no report is ever read as a note. Covered by the `~/code` rule above; listed so the path is on record. |

Not allowed, on purpose: `rm` (the classifier judges each delete; the verifier's walk spec and the merger's `worktree remove --force` on a fresh retry are the only ones the roles make), `vercel`, `supabase` and `migrate:production` (the live-key deny refuses them in a graduated repo, and a rehearsal never deploys), and any `Bash(sudo:*)`.

## Deny

| Rule | Why |
| --- | --- |
| `Bash(git push:*)` | No role pushes; the push is Abdul's. In `~/.claude/settings.json` on 2026-11-04 this rule sits under `ask`, not `deny`, and the `deny` list is empty: an `ask` rule prompts Abdul in his own session and stops an agent that has no one to answer, so it holds the push for him either way; a `deny` would refuse his own authorised pushes too. Left under `ask` on Abdul's decision, 2026-11-04. A `git -C <tree> push` escapes a prefix rule, so the merger's file says never, and the first real run reads its log for one. A hook that refuses `push` in a `git -C` command is the mechanical road if the log ever shows one. |

## The JSON

```json
{
  "permissions": {
    "allow": [
      "Read(~/.claude/skills/**)",
      "Workflow",
      "Bash(python3 ~/.claude/skills/workflow/lib/*)",
      "mcp__ccd_host__request_keep_awake",
      "PushNotification",
      "ScheduleWakeup",
      "TaskStop",
      "Bash(git:*)",
      "Bash(node:*)",
      "Bash(npm:*)",
      "Bash(npx:*)",
      "Bash(cp:*)",
      "Bash(mkdir:*)",
      "Bash(psql:*)",
      "Bash(curl:*)",
      "Edit(~/code/**)",
      "Write(~/code/**)",
      "Edit(~/.claude/pending.md)"
    ],
    "deny": [
      "Bash(git push:*)"
    ]
  }
}
```
