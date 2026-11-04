# README outline for version 2

The prototype for "How the README tells the version story", as Abdul approved it on 2026-10-30. The first reader is a future employer who arrives from LinkedIn and judges on the first screen. Part 1 is that screen, written out in full. Part 2 is the rest of the page, one line per section. Square brackets mark a figure nobody has measured yet.

## Part 1: the first screen

> # agent-skills
>
> I built an autonomous software pipeline for Claude Code, with 33 hooks and a second agent on every change whose only job was to find a reason to reject it. It built Orderflow, which now runs the orders of a real business, in six weeks and 2,528 commits. Then I measured where the time went and cut most of it.
>
> What survived fits on one page. A fast lane gives an idea four days to become a live MVP, and a careful lane takes over the day a real customer arrives. The target is a new product every two to four weeks.
>
> | What I run | Version 1 | Version 2 |
> |:--|--:|--:|
> | Skills | 35 | 23 |
> | of them my own | 11 | 5 |
> | Hooks | 33 | 6 |
> | Agent definitions | 16 | 7 |
> | [the measured cost, per shipped feature] | [v1 figure] | [after three products] |
>
> ```
> claude plugin install workflow --marketplace roufmlp/agent-skills
> ```
>
> The plugin holds my four public skills, seven agents and four hooks. It installs Matt Pocock's skills beside them, because 18 of the skills I use are his.

## Part 2: the rest of the page

1. **How it works.** One left-to-right diagram: idea log, brainstorm session on the 1st and 15th, brief, prototype, MVP, graduation, change notes. Then one short paragraph per lane, with its done test.
2. **Where a reminder failed, a hook refuses.** The four hooks that ship, what each refuses, and the failure that put it there.
3. **What the plugin holds.** One table of the four skills, seven agents and four hooks: name, job, lane. Matt Pocock's 18 skills get one line and a link to his repository.
4. **Products.** Graduated products only: name, one line, days from idea to live, and a link where the product is public. MVPs never appear. The section stays out until the first product graduates.
5. **Install.** The command, then auto-update on in `/plugin`. Needs Claude Code 2.1.292 or later, git, and Python 3 for the hooks; on Windows a hook error shows until Python is installed, and nothing is blocked. Then the GitHub Copilot app: skills and agents only, in steps written from the first install at work.
6. **Version 1.** A link to the `v1` tag, with the five-issue case study and the record of how the model and effort levels were chosen. One paragraph on why each part retired, linking the map and the spec that decided it.
7. **Credits and licence.** Matt Pocock's skills, MIT. This repository, MIT.

Rejected openings: one led with Orderflow as the proof, and one with the principle that agents forget reminders but cannot get past checks.
