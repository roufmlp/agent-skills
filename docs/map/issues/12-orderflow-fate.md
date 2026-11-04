Status: resolved
Assignee: Abdul (wayfinder session 2026-10-30)
Type: grilling
Blocked by: 03

# What happens to Orderflow

## Question

Orderflow is finished and runs the orders of a real business (Abdul, 2026-10-30), so it already holds real data, and "How the README tells the version story" names it on the README's first screen as what version 1 built. What does it take to move Orderflow into the careful lane: a fresh run of the pre-launch gate, anything else a graduating MVP gets, or nothing? And what happens to its 728 issue files and any issues still open? "One repo that is safe to publish" made product names public, so the public repository can name Orderflow; it cannot name the business Orderflow is built for.

Noted by "What version 1 cost, and where its time went" (2026-10-30): at the last commit on main on 24 October, 622 of the 728 issue files were done (578 through runs, 25 by the direct road, 19 another way), 73 parked, 29 closed and 4 waiting for hardening. Today Orderflow holds 753 issue files, 650 of them done.

## Answer

Orderflow is already a product: real orders have gone through it since its pilot started on 26 October. It joins the careful lane at the switch and goes back through no fast-lane step. Until then version 1 applies in full. The live request-kinds run finishes on the chain, because the app is in production and a half-built feature would reach the pilot.

Before request-kinds merges, Abdul pushes the commits already waiting on local main, so its first push carries nothing else. Then the loop runs:

1. The run ends. Its findings become issue files or refusals, and the merge briefing names every carve.
2. Abdul merges to local main, and each carve becomes an issue file.
3. He tests on local main, and each bug he reports becomes an issue file.
4. He pushes when no bug blocks a pilot user. On the day of each push that carries a migration, the pre-launch gate runs again and he applies the migrations.
5. Carves, findings and bugs go through `/harden-issues` and `/run-issues` on his command. Steps 2 to 5 repeat until he says request-kinds is finished.

Abdul picks the switch day. Version 2 must be built, he must have said request-kinds is finished, and no run may be in progress. Orderflow's part of the switch then takes four sessions, in this order:

1. The sweep. One session reads `.scratch/` and checks each open risk-class item against the code as it stands that day. An item that still holds becomes a draft change note in `changes/`. The items are the 28 parked issues that touch a risk class, the 31 high-severity rows still open in the hunt register, and any request-kinds issue still open. In `.scratch/orderflow-v1/issues/`, the 28 are 55, 56, 58, 61, 63, 80, 83, 85, 89, 93, 98, 160, 173, 187, 409 and 588, which touch a risk class in shipped code or data, and 48, 49, 51, 52, 53b, 57, 73, 74, 78, 82, 86 and 90, which test one.
2. The brief: one page written from the live app and `docs/`, with the main flow, what is not built yet, links to the area prototypes and the graduation line for 26 October.
3. The cleanup, in one session. It tags `v1`, moves the test inputs in `.scratch/` into `tests/` (the prototype screenshot pairs among them) and `rulings.md` into `docs/`, points the nine files that read them at the new paths, and removes `.scratch/` from main. It comes after the sweep, which reads `.scratch/`.
4. The evening check. The 18:00 job that reads problem reports stops starting fixes. It sorts the reports and sends Abdul one page with a draft change note for each bug, and a fix starts only when he asks.

Everything else stays readable at the `v1` tag and nothing is deleted. That covers all 753 issue files, the 46 unfinished ones outside the sweep among them, the rest of the register and the 1,312 open queue items. Turning those into change notes would carry version 1's backlog into version 2. The risk-class items get a fresh look because they are the ones that can cost a real business money or data.

The pre-launch gate ran again on 31 October. Seven of its ten rows passed. Row 5 failed because production runs Next.js 16.3.5, which carries three critical remote-code-execution advisories that 16.4.1 fixes, and Abdul approved an issue file for the direct road. Rows 9 and 10 wait on his own checks of account MFA and the Supabase Security Advisor. From here the gate runs on each request-kinds push day that carries a migration, so the switch runs none of its own.

`CONTEXT.md` now says a brief defines an MVP or a product, and that a product built on version 1 switches with the setup.

Procurement and two smaller repos still hold chain work, and they differ from Orderflow, so they went to a ticket of their own: "What happens to procurement and the other chain work". "How the careful lane keeps every slice aligned to the core design" and "Which steering files each lane loads, and the new CLAUDE.md" carry notes on what this answer changes for them.

Changed by "How the careful lane keeps every slice aligned to the core design" (2026-10-31): the cleanup no longer moves the 290 prototype screenshot pair folders (317 MB) into `tests/`. They stay at the `v1` tag with the fidelity tool, because the screenshot baseline is now taken from the live app on the switch day. The brief session also writes Orderflow's core design from `docs/patterns.md`, `docs/visual-direction.md` and its two ADRs, and Orderflow keeps its existing checks.

Changed by "Which steering files each lane loads, and the new CLAUDE.md" (2026-10-31): the cleanup session also rewrites Orderflow's `CLAUDE.md`. It adds the careful lane block, turns "Issue tracker" into "Change notes", retires "After a run", gives "The evening check" the sorts-only rule that leaves the global file, swaps the frozen-prototype section for the core design, and points pending items at `~/.claude/pending.md`.

Changed by "Whether version 2 is built in two stages" (2026-11-01): version 2 is built in two stages, and "version 2 must be built" now means stage two. Until then Orderflow's smaller features run on version 1. Multitenancy does not, and one small feature is held back as the careful lane's first test. Step 4 of the switch moves earlier: the evening check stops starting fixes now, as a version 1 action.

Changed by "How a product graduates, stops or switches over" (2026-11-01): a fifth switch session writes Orderflow's core design, its checks and its baselines by running steps 3 and 4 of the graduation checklist. The screens come from the route tree and the modules from the folders under `src/` and the existing boundary checks, because the four named sources hold neither. The baselines come from the local app on seed data, not from the live app.
