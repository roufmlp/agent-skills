# Inventory of skills and hooks

Type: research. Resolves ticket 04, "What each skill and hook does today". Feeds ticket 08, "What the careful lane keeps". It decides nothing.

**The buckets are a draft, not decisions.** Every bucket below is a first sort made from each skill's frontmatter and body and each hook's docstring. Ticket 08 and the later spec may move any row.

## How to read the buckets

- **fast lane**: a light helper that works with no ceremony and needs no chain. Usable in any lane.
- **careful lane**: part of the build discipline a graduated product would keep.
- **version 1 record only**: tied to the chain (issue files, register, queue, daily brief). Kept as history for the version 1 to version 2 story, not carried forward.
- **personal, never public**: Abdul's own material. Stays off any public repo.

"Holds private material" is yes when the files name Abdul, his projects, his home paths, his emails or his rulings. A scan of the repo counted the hits. "No" means the scan found none.

## Counts that differ from the ticket

- The ticket says 35 skill folders. The repo has 37 folders. Two of them, `docs` and `lib`, are not skills (no `SKILL.md`). The other 35 are skills.
- The ticket says 31 hooks. `~/.claude/settings.json` registers 34 hook commands that point at 33 distinct scripts. `machine-preflight.py` is registered twice (SessionStart and UserPromptSubmit).
- Two more files in `~/.claude/hooks/` are not registered. `run-issues-risk-path-guard.py` is a full guard (339 lines) whose docstring says it is registered, but `settings.json` does not list it. `risk_path_reader.py` is a helper module it imports. The unregistered guard has its own row below.
- The hooks live in `~/.claude/hooks/`, outside this repo. Today they are not in any public repo.

## Skills (35)

Chain steps: to-prd, to-issues, harden-issues, run-issues, parallel-hunt, daily-brief, general.

| Name | One-line job | Chain step | Holds private material | Draft bucket |
|---|---|---|---|---|
| ask-matt | Router that tells you which skill fits your situation | general | yes, light: one note naming `~/.claude/CLAUDE.md` | version 1 record only |
| codebase-design | Shared vocabulary for deep modules, seams and testability | general | no | careful lane |
| coderules | Pointer that loads Abdul's code and security rules | general | yes: absolute home path, names the CoWork vault; the rules file it loads is his | careful lane |
| daily-brief | Collates every queued decision into one daily file and writes his answers back | daily-brief | yes: 29 Abdul mentions, 36 home paths, procurement memory paths, 2 service names | version 1 record only |
| designrules | Pointer that loads Abdul's design rules | general | yes: absolute home path, names the CoWork vault | careful lane |
| diagnosing-bugs | Diagnosis loop for hard bugs and slow code | general | no | fast lane |
| domain-modeling | Builds the glossary (`CONTEXT.md`) and architecture decision records | general | no | careful lane |
| grill-me | Thin wrapper that runs a `/grilling` interview | general | no | fast lane |
| grill-with-docs | Runs `/grilling` and writes glossary and decision records as it goes | general | no | fast lane |
| grilling | Interviews you in rounds over a decision tree, with a recommended answer each time | general | no | fast lane |
| handoff | Writes a handoff document so a fresh session can continue | general | no | fast lane |
| harden-issues | Attacks the acceptance criteria of issue files before anyone builds | harden-issues | yes: 101 Abdul mentions, 32 home paths, OrderFlow and procurement examples, a `decisions.md` of rulings | careful lane |
| implement | Implements a spec or tickets, test-first through `/tdd` | general | no | fast lane |
| improve-codebase-architecture | Finds deepening refactors and shows them as an HTML report | general | no | careful lane |
| panel-review | Multi-perspective review of a document or design, ending in a verdict | general | yes, light: 7 Abdul mentions, home paths | careful lane |
| parallel-hunt | Finder and fixer run concurrently over a bug register with adversarial gates | parallel-hunt | yes: 23 Abdul mentions, 21 home paths, Zoho and Vercel names, `decisions.md` | careful lane |
| premise-check | Checks every factual claim in named issues against main before a run | run-issues | yes: 12 Abdul mentions, 8 home paths | version 1 record only |
| prototype | Builds a throwaway prototype to answer a design question | general | no | fast lane |
| questionrules | Pointer that loads what a question to Abdul must carry | daily-brief | yes: absolute home path; the rules file it loads is his | version 1 record only |
| research | Sends a background agent to read primary sources and write findings to a file | general | no | fast lane |
| resolving-merge-conflicts | Steps for resolving a merge or rebase conflict | general | no | fast lane |
| run-compare | Answers whether the pipeline is getting cheaper, faster or better across runs | run-issues | yes, light: 2 Abdul mentions, a home path | version 1 record only |
| run-issues | Implements a range of issues with fresh workers, verify and review gates and a merge gate | run-issues | yes, heavy: 142 files, 522 Abdul mentions, 253 home paths, 116 OrderFlow and procurement mentions, 2 real-looking email addresses (his Gmail and one other), dated panel-review and redesign records | careful lane |
| setup-matt-pocock-skills | Configures a repo's issue tracker and label vocabulary for the engineering skills | general | yes, light: one home path | version 1 record only |
| tdd | Test-first loop (red, green, refactor) with a seam rule | general | yes, light: 1 Abdul mention, 2 home paths | careful lane |
| teach | Teaches a topic over several sessions in a learning workspace | general | no | fast lane |
| to-issues | Breaks a PRD into issue files as vertical slices and calls `/harden-issues` | to-issues | yes: 6 Abdul mentions, 8 home paths | careful lane |
| to-prd | Turns the conversation into a PRD file under `.scratch/` | to-prd | yes, light: 1 Abdul mention, 2 home paths | careful lane |
| to-questionnaire | Turns a decision you cannot answer into a questionnaire for someone else | general | no | fast lane |
| triage | Moves issues through a triage state machine; out of the chain since 2026-07-27 | general | yes, light: 1 Abdul mention, a home path | version 1 record only |
| wait-what | Asks the agent to re-pitch its last message in plain terms | general | no | fast lane |
| wayfinder | Plans large work as a map of decision tickets and resolves them one by one | general | no | fast lane |
| wizard | Generates a bash wizard that walks a human through manual steps | general | no | fast lane |
| writing-for-agents | Guide for writing skills, `CLAUDE.md` and other agent-read documents | general | no | fast lane |
| writingrules | Pointer that loads Abdul's writing rules | general | yes: absolute home path, names the CoWork vault; the rules file it loads is his voice | personal, never public |

Not skills, but in the same repo: `lib/` holds 44 shared scripts and tests used by the chain skills (`check_*`, `collect_shards.py`, `rulings.py`, `next_batch.py`) and carries 154 Abdul mentions, 95 home paths and 59 OrderFlow and procurement mentions. `docs/agents/risk-paths.md` is a risk-path list that `lib/set_level.py` reads; the scan found no private hits in it. `UPSTREAM.md` tracks 24 skills copied from Matt Pocock's public repo. Of those, 18 are clean copies. Six are forks that carry Abdul's rules or names: `ask-matt`, `setup-matt-pocock-skills`, `triage`, `to-prd`, `to-issues` and `tdd`.

### Agent files in `~/.claude/skills/workflow/agents/` that belong to a skill (16)

| Skill | Agent files |
|---|---|
| harden-issues | harden-issues-attacker, harden-issues-seam |
| run-issues | run-issues-implementer, run-issues-implementer-escalated, run-issues-review-gate, run-issues-review-gate-critical, run-issues-verify-gate, run-issues-finale |
| parallel-hunt | parallel-hunt-finder, parallel-hunt-fixer, parallel-hunt-claim-gate, parallel-hunt-fix-gate, parallel-hunt-fix-gate-critical |
| run-issues and parallel-hunt | promotion |
| panel-review | panel-review-persona, panel-review-gate |

These follow their skill's bucket. The scan did not open the agent files for private hits; they are Abdul's briefs and likely carry his name and rulings.

## Hooks (33 registered, 1 not registered)

All hooks live in `~/.claude/hooks/` and are registered in `~/.claude/settings.json`. Every docstring names Abdul or the run that caused the rule, so "private material" below says what is specific. Unless the row says otherwise, the private part is the docstring only (his name, run ids, ruling dates), not the logic.

| Name | One-line job | Chain step | Holds private material | Draft bucket |
|---|---|---|---|---|
| browser-budget | Blocks every Nth screenshot call to force a subagent or script question | general | yes, light: one Abdul mention | fast lane |
| coderules-gate | Blocks the first code edit of a session until the code rules are read | general | yes, light: home path to the rules file | fast lane |
| fixed-sleep-guard | Refuses a fixed wait over 30 seconds typed through an inline interpreter | general | yes: 2 Abdul mentions, OrderFlow run id and issue number | fast lane |
| git-shared-state-guard | Refuses git commands that reach across sessions in one checkout | general | yes: Abdul mention, procurement ticket | fast lane |
| headless-chrome-guard | Refuses starting Chrome without the keychain and media flags | general | yes, light: 2 Abdul mentions | fast lane |
| machine-wide-kill-guard | Refuses a kill that selects processes by pattern, not by pid | general | yes, light: Abdul mention, run id | fast lane |
| worktree-base-drift | Brings a harness bridge worktree up to local main at session start | general | yes: 4 Abdul mentions, OrderFlow measurement | fast lane |
| generated-file-guard | Refuses hand writes to the generated `register.md` and `decisions-queue.md` | general | no personal names; cites map tickets 38 and rulings | version 1 record only |
| origin-row-guard | Refuses a register row that does not name where the fault came from | parallel-hunt | yes, light: 2 Abdul mentions, map ticket 37 | version 1 record only |
| run-state-path-guard | Refuses writes to retired run-state file names and names the new path | run-issues | yes, light: 2 Abdul mentions | version 1 record only |
| rulings-write-guard | Refuses a write that would leave an unreadable entry in `rulings.md` | general | yes: 5 Abdul mentions, OrderFlow rulings file | version 1 record only |
| retired-phrases-gate | Refuses superseded wording in steering files | general | no personal names; reach is his `~/.claude` steering files | version 1 record only |
| issue-size-guard | Refuses an issue file write that leaves it over 1 MB or ten times its size | to-issues | yes: Abdul mention, OrderFlow run and issue ids | version 1 record only |
| number-claim-guard | Refuses a write to an issue or migration file whose number nobody claimed | to-issues | yes, light: 2 Abdul mentions | version 1 record only |
| worktree-snapshot-notice | Tells the session at start that a worktree's queue and register are frozen | daily-brief | no | version 1 record only |
| pilot-database-guard | Refuses a Bash command that writes to the pilot customer's database | run-issues | yes, heavy: procurement pilot, home path, a service name, 3 Abdul mentions | personal, never public |
| machine-preflight | Measures RAM and swap before a long run and refuses it when the machine cannot survive; checks the approved Claude Code version pin | run-issues | yes: 5 Abdul mentions, his Mac's kernel panic report | careful lane |
| gate-source-write-guard | Refuses a gate's write to shipped source inside a live run's tree | run-issues | yes: 8 Abdul mentions, 3 procurement mentions | careful lane |
| gate-issue-write-guard | Refuses a gate's write to an issue file or another gate's verdict | run-issues | yes: 3 Abdul mentions | careful lane |
| gate-commit-guard | Refuses a `git commit` by a gate; the runner commits | run-issues | yes, light: Abdul mention, commit ids | careful lane |
| copy-delete-guard | Refuses a delete that reaches the real tree through a link in a private copy | run-issues | yes, light: Abdul mention | careful lane |
| gate-copy-guard | Refuses copying a repo to the temp folder by any road but `make_copy.py` | run-issues | yes, light: Abdul mention, a skills commit id | careful lane |
| model-map-gate | Holds every loop spawn to the model map the run ledger records | run-issues | yes, light: Abdul mention | careful lane |
| model-landed-check | Reports after each spawn whether the requested model actually ran | run-issues | yes, light: 2 Abdul mentions | careful lane |
| run-issues-sweep-gate | Refuses the runner's commit until that issue's register rows are swept | run-issues | yes: 2 Abdul mentions, procurement | careful lane |
| run-issues-foreground-gate | Refuses a spawn whose `run_in_background` value is wrong for its type | run-issues | yes, light: 2 Abdul mentions | careful lane |
| run-issues-evidence-gate | Refuses a gate spawn that has no implementation record to judge | run-issues | yes: Abdul mention, 3 procurement mentions | careful lane |
| run-issues-parallel-gates | Refuses a gate spawned after its partner has already returned | run-issues | yes: 3 Abdul mentions, 3 procurement mentions, a home path | careful lane |
| run-issues-criteria-fault | Refuses another implementer attempt while a gate-filed criteria fault stands | run-issues | yes, light: Abdul mention, run ids | careful lane |
| run-issues-brief-cap | Refuses a first-attempt implementer brief over the word cap | run-issues | yes: 4 Abdul mentions | careful lane |
| run-issues-typecheck-gate | Refuses a gate spawn while the run's tree does not typecheck | run-issues | yes, light: Abdul mention | careful lane |
| run-issues-wakeup-gate | Refuses a spawn while the ledger names no wakeup cron | run-issues | yes, light: 2 Abdul mentions | careful lane |
| run-issues-suite-gate | Refuses a whole test suite in a run unless it goes through the wrapper | run-issues | yes: Abdul mention, OrderFlow cost figures | careful lane |
| run-issues-risk-path-guard (not registered) | Refuses a light issue's implementer a write to a path the risk file names | run-issues | yes, light: Abdul mention; imports `risk_path_reader.py` | careful lane |

Support files beside the hooks: `heavy-run-version.pin` (approved Claude Code versions for a heavy run), `TOOL-SET-PROBE.md` (what that pin means), `risk_path_reader.py` (helper module), and one `test_*.py` per guard.

## Counts per bucket

| Bucket | Skills (35) | Hooks (33 registered) | Hooks incl. 1 unregistered (34) |
|---|---|---|---|
| fast lane | 15 | 7 | 7 |
| careful lane | 12 | 17 | 18 |
| version 1 record only | 7 | 8 | 8 |
| personal, never public | 1 | 1 | 1 |
| Total | 35 | 33 | 34 |

## Notes for ticket 08

- The careful-lane hook count depends on one thing: whether `run-issues` stays in some form. 17 of the 18 careful-lane hooks guard its runs. If it goes, they move to version 1 record only.
- The fast lane is where the clean upstream copies sit. All 15 fast-lane skills have no private hits at all; this is the cheapest part of a public repo.
- Private material is not spread evenly. `run-issues` (142 files), `lib` (44 files), `harden-issues` and `daily-brief` hold most of it. The four pointer skills (`coderules`, `designrules`, `writingrules`, `questionrules`) hold little themselves but point at files in his CoWork vault and home folder.
- The scan counted name, path, email and project-name hits. It did not judge whether a hit is a real secret. The one hard secret check, for `sk-` style keys, found none. Ticket 06 owns the full sweep.
