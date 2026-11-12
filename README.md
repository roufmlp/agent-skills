# agent-skills

I built an autonomous software pipeline for Claude Code, with 33 hooks and a second agent on every change whose only job was to find a reason to reject it. It built Orderflow, which now runs the orders of a real business, in six weeks and 2,528 commits. Then I measured where the time went and cut most of it.

What survived fits on one page. A fast lane gives an idea four days to become a live MVP, and a careful lane takes over the day a real customer arrives. The target is a new product every two to four weeks.

| What I run | Version 1 | Version 2 |
|:--|--:|--:|
| Skills I use | 35 | 23 |
| of them my own | 11 | 6 |
| Hooks | 33 | 7 |
| Agent definitions | 16 | 16 |
| Minutes of build session per shipped change | 69 | measured after three products |

```
claude plugin install workflow --marketplace roufmlp/agent-skills
```

The plugin holds my six public skills, sixteen agents and four hooks. It installs Matt Pocock's plugin beside them, 38 skills, because 17 of the skills I use are his.

## How it works

```
ideas repo ──▶ brainstorm (1st, 15th) ──▶ brief ──▶ prototype ──▶ MVP ──▶ graduation ──▶ change notes
                                          └───────── fast lane ─────────┘   └──── careful lane ────┘
```

The fast lane is for a product with no customer yet. A brief of one page, a prototype to settle the screens, then one build session that ends when the done checks pass: for a site, the checks in `skills/site-checks`. Nothing in the lane asks me a question mid-run; each session takes a default, writes it down and reports at the end.

The careful lane starts on the day real users or real data arrive. `/build-feature` interviews me once, writes the feature as change notes of half a page each, with the tests that prove them, and I approve the plan. A workflow then builds each note in a fresh agent, test-first, and two more agents try to reject it: one runs the checks and walks the screens with hostile input, one reads the diff. The final check runs the whole suite on the merged feature before it reaches main, and nothing pushes.

A run does not wait at my keyboard. A note that stops on a question sends it to my phone with the agent's written default; after fifteen minutes with no answer the default rules, and the run starts again by itself. A question about money, access, a migration's direction or data leaving the product never takes a default. One agent first looks for a road the question does not offer. Three readers then judge every road, each from the seat of someone who pays when it is wrong: the person the rule protects, me on release day, and the next agent to build on the code. A count of their three answers decides, and no agent is the judge: two on one road and it rules, two that ask for a fact first and the note waits for me, no two alike and the written default rules. A note that fails three times gets one more try on the change its last reject report asks for, and waits for me if it fails again. Whatever was decided without me is listed in the report, and the feature stays off main until I have confirmed each line. A ruling or an answer in my name must quote a whole message or sentence I typed in that session after I was shown the question, and git hooks hold main, and the push of it, while a line waits. The hooks stop the easy roads; `skills/build-feature/when-a-run-stops.md` lists what they do not stop.

## Where a reminder failed, a hook refuses

Every rule that an agent forgot often enough became a script. These four ship:

| Hook | Refuses | What put it there |
|---|---|---|
| `coderules-gate` | The first code edit of a session before the code rules are loaded | Sessions skipped the rules whenever the first edit looked small |
| `git-shared-state-guard` | `git add -A`, `git stash`, `--no-verify`, a change to `core.hooksPath`, and any wide commit in a checkout other sessions share | Two sessions staged each other's work in one day |
| `machine-wide-kill-guard` | A kill that selects processes by pattern, such as `pkill -f vitest` | A gate killed the test runner of every session on the machine |
| `headless-chrome-guard` | A Chrome launch without the flags that keep it out of the keychain and away from Apple Music | Keychain dialogs and a music app opening in the middle of runs |

A refusal names what to do instead. None of them can be skipped from an agent's shell, because the guard refuses the skip too.

## What the plugin holds

| Name | Job | Lane |
|---|---|---|
| `coderules` | The code rules and the pre-launch gate; its body is the rules | both |
| `designrules` | The design rules for any screen, page or document | both |
| `site-checks` | The done checks a site runs before it is called done | fast |
| `build-feature` | The interview, the plan, the run, the rulings and the gate before main | careful |
| `panel-review` | A review of a document by several perspectives, with a gate on the findings | both |
| `parallel-hunt` | A bug hunt: a finder and a fixer over a shared register, with gates on every claim and fix | careful |
| 9 `build-feature-*` agents | Implementer, verifier, reviewer, note checker, merger, final verifier, final reviewer, ruling reader, road finder | careful |
| 5 `parallel-hunt-*` agents | Finder, fixer, claim gate, fix gate and its critical form | careful |
| 2 `panel-review-*` agents | Persona and gate. The persona also sits as each of the three readers of a risk-class question | both |
| `workflows/build-feature-run.js` | The script that drives the agents, three notes at a time | careful |
| `templates/` | The brief, the product `CLAUDE.md`, a change note, a plan, a report and the git hooks a product installs | both |

The other 17 skills I use come from [Matt Pocock's plugin](https://github.com/mattpocock/skills), which installs with this one and carries 38 in all. `budget.md` sets the counts above; a check in the Action fails when a push goes past them.

## When something stops

A run that stops leaves its state in the feature's report. The cases, from the rehearsals:

| What you see | What to do |
|---|---|
| A note row reads `failed` after three strikes | Nothing. The session changes the note as its last reject report asks and starts again, once per note |
| A note row reads `stopped:` with a question | Answer on your phone inside fifteen minutes. After that the written default rules, or for a risk-class question the count of three readers, and the run starts again |
| A note row reads `waiting:` | Only you rule on it: a risk-class question the readers held for a fact, a question with no typed class, a second failure, or a tool fault with no listed repair. `/build-feature <name>` opens on the row; the other notes ran on |
| A note row reads `stopped: tooling:` | A hook, a check script or the app refused a step. The session applies the listed repair and starts again; no gate is loosened |
| `State: held` | The final check passed, and rulings made without you wait for your answer. `/build-feature <name>` lists them; the merge follows your last answer |
| `stopped: API errors` | A usage limit or an outage. Wait for the reset, then start again; merged notes are kept |
| The final check ends on `FINDINGS` | Three fix rounds did not clear it. Fix the feature branch in a session of its own, then start again |
| `On main:` lines in the final check | Faults main already has. Nothing for this run |

The full table, with every case seen so far, is in [`skills/build-feature/when-a-run-stops.md`](skills/build-feature/when-a-run-stops.md).

## Install

```
claude plugin install workflow --marketplace roufmlp/agent-skills
```

Inside a session the same command reads `/plugin install workflow --marketplace roufmlp/agent-skills`. It needs Claude Code 2.1.292 or later, git, and Python 3 for the hooks. On Windows a hook error shows until Python is installed, and nothing is blocked. Plugins from outside Anthropic's marketplace do not update on their own: switch auto-update on once in `/plugin`, and each release reaches you a session or two later.

The GitHub Copilot app installs the same plugin from its marketplace page and gets the skills and agents; the hooks are not meant to run there. The steps from the first install at work are not written yet.

To work on the plugin, clone it to `~/.claude/skills/workflow/` and run `sh .githooks/prepare`. Claude Code loads a plugin folder there at every session start, and the `commit-msg` hook then refuses a commit that carries a private name or your home path.

## Version 1

Version 1 is at the [`v1` tag](../../tree/v1): the issue runner, the parallel hunt, 33 hooks and the run records. Two records are worth reading on their own: [the five-issue case study](docs/case-study-five-issue-run.md) and [how the models and effort levels were chosen](docs/model-and-effort-choices.md), which found that a setting nothing read had been there from the start.

Most of it retired because the time went elsewhere than the build loop. A version 1 issue took 69 minutes of run time, but more than half the commits in Orderflow's window landed outside any run, in sessions that answered questions, carried decisions and kept the records. The map that decided what to keep is in [`docs/map`](docs/map/spec.md), one file per question.

## Credits and licence

Matt Pocock's skills, MIT. This repository, MIT.
