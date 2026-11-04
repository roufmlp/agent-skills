Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: grilling
Blocked by: 25

# Where the note check lives, and baselines for changed screens

## Question

The note check refuses a diff that strays from its change note, and four tickets lean on it. [The walkthrough](../research/25-walkthrough.md) found it has no home, gap C6, and that the screenshot baselines only cover screens that do not change, gap C7.

The plugin ships four hooks and its budget starts at four, and the note check is not one of them. Nothing says whether it is a git hook or a Claude Code hook, who installs it in Orderflow (whose `core.hooksPath` is empty), or how it maps a commit to its note. Separately, the feature's second note puts a bubble in the header of every signed-in screen, and "any difference fails" the screenshot test. No ticket names who retakes the baselines for screens a note changes on purpose, at which step, or whether Abdul approves changed ones the way he approves new ones. Nor does any say whether an edit to the shared signed-in layout counts as touching every route under the "Screens:" rule.

Decide the note check's kind, install and commit-to-note map, and who retakes and approves baselines for changed screens.

The lighter option: the note check is a git hook in each product repo, installed by the graduation checklist and matched by a note id in the commit message; the note's verifier retakes the baselines for the screens its "Screens:" line names, and Abdul approves them in the feature report with the new ones. A heavier answer says what this would cost.

Changed by "Whether version 2 is built in two stages" (2026-11-01): this ticket belongs to stage two, the careful lane. It is grilled on paper while stage one runs.

Changed by "How a change goes live" (2026-11-01): each product repo also gets a `pre-push` git hook that refuses a push carrying a migration `migrate:production` has not applied. It installs the same way as the note check, so decide both together.

Changed by "How a product graduates, stops or switches over" (2026-11-01): the graduation checklist exists, as a file in the plugin. Its step 7 installs the git hooks, so whatever this ticket decides for the note check and the `pre-push` hook goes there.

Changed by "What a run does when notes collide or fail" (2026-11-01): a third check needs the same home. It refuses two migrations with the same number on a branch, and runs when the merger merges a note into the feature branch and when local main merges into a feature branch.

## Answer

Abdul took the lighter option on every part, on 2026-11-01, with three changes: the branch names the note rather than the commit message, the final verifier retakes changed baselines rather than each note's verifier, and the red check runs on every merge into main. The plugin's hook budget stays at four.

**Three git hooks in each graduated repo (C6).** The note check, the duplicate-number check from "What a run does when notes collide or fail" and the migration check from "How a change goes live" all live in git hooks, committed in the product's `.githooks/`. A git hook fires on every commit, whichever tool made it, and on Abdul's own commits too. A Claude Code hook would see only the agent commands it can parse, and would be a fifth hook in the plugin. Each hook is a few lines that call one script in the plugin at Abdul's working copy, `~/.claude/skills/workflow/`. The careful lane covers his own products on his own Mac, so that path is fixed. When the script is missing, the hook refuses. A copy of the script in each product would drift from the others.

| Hook | Runs |
| --- | --- |
| `pre-commit` | The note check and the duplicate-number check |
| `pre-merge-commit` | The duplicate-number check, and on a merge into `main` the red check for the whole feature |
| `pre-push` | The migration check |

A fast-forward skips `pre-merge-commit`, so the install sets `branch.main.mergeoptions=--no-ff`. Each new test in a feature must fail on main's code from before the feature, which a test that failed on the code from before its own note also does. So the red check that "Whether the build agents work test-first" ran only for a one-note change now runs at every merge into main, and the special case goes.

**Install.** Graduation step 7 commits `.githooks/` and sets `core.hooksPath` and the merge option. Git does not copy local config in a clone, so a `prepare` script in `package.json` sets both again on every `npm install`, and a fresh clone on a new Mac gets the hooks. The suite script refuses to run when `core.hooksPath` is wrong, so no check passes in a repo without its hooks. At the switch, the fifth switch session runs step 7 on Orderflow along with steps 3 and 4; no ticket named who installs there, and this is a default.

**Skipped hooks.** `--no-verify` and `-c core.hooksPath=` skip every git hook, and nothing in version 2 refuses them today. git-shared-state-guard, already in the plugin, refuses both on an agent's git command, and refuses an agent command that changes `core.hooksPath`. A second run of the note check by the final verifier would only catch commits made outside the Bash tool, and no role makes one.

**Commit to note.** The branch names the note: `feature/report-a-problem/02` maps to note 02 in `changes/report-a-problem/`. The run sets the branch, so no agent has to remember an id. A commit on `feature/<name>` itself maps to every note already merged, which covers the merger's commits and the final verifier's baselines. A commit on a branch that maps to no note may not touch a guarded path: a baseline, `docs/design.md` or a screen's route folder.

**Changed screens (C7).** A note's verifier compares every screen the note does not name, and a difference is a strike. It walks the screens the note names and does not compare them. The final verifier retakes the baselines of every named screen once, on the merged branch, and the merger commits them, as it already does for a new screen's first baseline. Two parallel notes that change the same screen would otherwise both commit a PNG and meet in a binary conflict. In a one-note change, the fresh verifier subagent retakes them before the merge. Abdul approves a changed screen as he approves a new one: he sees it before and after in the feature report, and his push is the approval. A screen he dislikes gets a follow-up note.

**Shared layouts.** A "Screens:" line may name a route group, such as `Screens: all signed-in`. The check maps the group to its screens from the screens part of the core design, and counts a change to a shared file in the group, such as `(signed-in)/layout.tsx`, as touching each of them. Note 02 names one group instead of about thirty screens.

`CONTEXT.md` now defines note check and baseline.
