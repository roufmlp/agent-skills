Status: resolved
Assignee: Abdul (wayfinder session 2026-10-30)
Type: grilling
Blocked by: 06

# One repo that is safe to publish

## Question

How does this live repo become safe to publish without a scrub step? Pin down where private material moves (the home folder, a git-ignored folder or the memory directory), what check refuses a commit that carries private material and where it runs, what happens to agent-skills (archive it as the version 1 record, delete it, or fold it in), and whether the `.scratch/` history goes public. "How the brainstorm session works" already created one private home: the `roufmlp/ideas` repo, which holds the idea log and the MVP list. "What the careful lane keeps" retired 12 skills, 27 hooks, nine agent files and the chain scripts in `lib/` to the version 1 record, so the version 1 record is now a known set.

## Answer

Version 2 lands in `agent-skills`, the repo that is already public, as new commits, and its last version 1 commit gets the tag `v1`. `claude-skills-live`, the private repo this map was written in, is archived as a private record and its history never goes public. Its 517 commits carry private material in hundreds of files, as "What in this repo is private" found, and rewriting them was rejected. From the switch on, Abdul works in the public repo itself, so nothing is copied and nothing is scrubbed.

Private material has four homes, none of them inside the public repo:

- `~/.claude/`, the private `claude-config` repo: CLAUDE.md, the rules, rulings, memory, pilot-database-guard, the skills that do not ship, such as writingrules, and the list of private names.
- `roufmlp/ideas`: the idea log and the MVP list, as "How the brainstorm session works" set out.
- Each product's own repo: its brief and its change notes.
- The archived `claude-skills-live`: the version 1 run history in `.scratch/`.

A git-ignored folder inside the public repo was rejected. One `git add -f` publishes it, and a git worktree does not carry ignored files, so a session in a worktree would not see it.

Client names and client email domains are private. Product names are public, Orderflow included. This replaces scrub rule 2 in the `agent-skills` MANIFEST, which kept product names out too. Abdul's own name may appear in the README, the docs and the maps, but skill and agent files name a role ("the human"), so an agent on a friend's machine does not call them Abdul. Today eight of the kept skill files carry Abdul's name or login and two name a client; the switch fixes all ten.

A git `commit-msg` hook in the public repo refuses any commit that carries a private name or the home-folder path. It checks the staged lines, the file names and the commit message, and in skill and agent files it also refuses Abdul's name and login. The script is public. The list of private names stays in `~/.claude/`, and the hook reads the home path, the name and the login from the machine. The hook runs before anything leaves the laptop, so a refused commit needs no push and no history rewrite: the agent replaces the text and commits again, and pushing stays Abdul's call. Three other places were rejected. A GitHub Action runs after the push, when the text is already public. A pre-push hook finds the text only once it sits in a commit, so the fix means rewriting history. A Claude Code hook sees agent sessions only and misses commits made any other way. Live keys stay with the hard deny that "What the careful lane keeps" added.

An agent may change the list or the hook only after Abdul approves that change in a Claude Code permission prompt. The same prompt guards the ways to skip the hook: `--no-verify`, `-c core.hooksPath=` and a change to the `core.hooksPath` setting. With nobody at the keyboard nobody can allow it, so a run the hook stopped cannot delete a name to get past it. A "yes" in chat would not do, because the agent would have to remember to wait for it. The [permissions docs](https://code.claude.com/docs/en/permissions) show an ask rule prompting even in auto mode. Bypass mode skips every prompt and nothing Abdul runs uses it, so the guard turns it off with `permissions.disableBypassPermissionsMode`. An installed mod that approves tool calls could also get past the prompt. The build session still has to confirm three things: that an `Edit` ask rule on the two files prompts in auto mode as the docs' Bash example does, that it catches shell commands that write them, such as `sed -i` or a redirect, and whether the sandbox can stop a program the agent writes to edit them, which no ask rule sees.

The list starts with today's clients and their email domains. A new client goes on it when Abdul takes the client on, added by an agent and approved by Abdul.

Version 1 stays restorable, with no end date. At the switch the last version 1 commits of `claude-skills-live` and `claude-config` are tagged as well, and both repos are archived; nothing is deleted. Going back takes an agent about 30 minutes: it checks out both tags and turns the scheduled tasks back on, and memory is untouched. A rollback restores the workflow, not the work done under version 2. Products keep their own repos and carry on, and skill changes made under version 2 stay behind. The longer version 1 sits unused, the likelier a Claude Code update breaks one of its old hooks.

One build session makes the switch, from version 1 to version 2, on the day Abdul stops using version 1. It tags the three version 1 commits, copies the version 2 skills into `agent-skills`, fixes the ten files, installs the hook, runs it over the whole tree and commits the lot as one change, so no version 2 commit carries private text. The sync step retires with its tools: the MANIFEST, `check_manifest_coverage.py` and `check_skill_drift.py`. Where Abdul's working copy sits is for "How someone installs it".

Everything in the public repo is public, future maps about the workflow included. The `.scratch/` history stays in the archived repo, with one exception: the spec and this map, with its tickets and research, go public with version 2, because they show how version 2 was decided. Nothing in the map names a client today, and the hook checks it at the switch anyway.

writingrules is already public, in the `steering/` folder of the version 1 pack, so "stays private" in "What the careful lane keeps" means it does not ship with version 2, not that it is secret.

`CONTEXT.md` now defines public repository, private name, version 1 record and switch.

Changed by "How someone installs it" (2026-10-30): the switch also tags and archives `claude-agents`, the version 1 repository behind `~/.claude/skills/workflow/agents/`, so a rollback restores the agents too. Abdul's working copy sits in `~/.claude/skills/workflow/`.
