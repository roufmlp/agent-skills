Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: grilling
Blocked by: 25

# How a product graduates, stops or switches over

## Question

Graduation is where every careful-lane artefact is born: the pre-launch gate, the core design, a check per pattern, import rules, baselines, the lane block in `CLAUDE.md`, a suite budget and, for another stack, the port. Seven tickets each add a part. [The walkthrough](../research/25-walkthrough.md) found nothing that holds them together, gaps F11, F12 and C1.

No skill, template or command holds the graduation list, and nothing says what starts the session. The brainstorm session where Abdul decides runs in the cloud and can do none of it. Stopping has the same hole, and part of it is Abdul's, because pausing a Vercel project asks him to type its name. A product named after its client meets the `commit-msg` hook once it is listed in the README. And Orderflow graduated before version 2 existed. The sources "What happens to Orderflow" names (`docs/patterns.md`, `docs/visual-direction.md`, two ADRs) hold no screen list with routes and no module map, Orderflow has no screenshot test, and no switch step writes them. Its live app holds real orders, while the tests run on seed data.

Decide whether graduation and stopping are a skill, a template or a checklist in the spec, who runs them and when, how a client-named product is listed, and what the switch writes for Orderflow's and procurement's core design.

The lighter option: one checklist in the spec, read by a local session Abdul starts after the brainstorm; the switch runs the same checklist on Orderflow and procurement; a client-named product goes in the README under a neutral name. A new skill counts against the plugin budget, so a heavier answer says why the checklist is not enough.

Changed by "Whether version 2 is built in two stages" (2026-11-01): this ticket belongs to stage two, the careful lane. It is grilled on paper while stage one runs.

Changed by "How an MVP's limits and its end are recorded" (2026-11-01): the kit site graduates at delivery during stage one, with the pre-launch gate only. Its core design and screenshot baselines are written when stage two lands, with Orderflow's and procurement's.

Changed by "How a change goes live" (2026-11-01): graduation turns the MVP's address into production. The checklist adds the host's Git link, so only Abdul's push deploys from then on; fills the "Production" line in `CLAUDE.md` that the hard deny hook reads; adds `migrate:production` when the product has a database; and installs the `pre-push` migration hook. A product that needs staging gets it here, with seed data only.

## Answer

Graduation and stopping live in one checklist file in the plugin, `checklists/graduate-stop.md`, beside the brief template and the `CLAUDE.md` template. Abdul starts the work by typing one word, `graduate` or `stop`, in a local session in the product's repo. He accepted each point below on 2026-11-01.

**A file, not a skill.** Every product's `CLAUDE.md` carries one line: "When Abdul says *graduate* or *stop*, follow `checklists/graduate-stop.md` in the workflow plugin." That line costs about 30 tokens, and only in sessions opened in a product's repo. The checklist itself, about 60 lines, loads only in a graduate or stop session. A `/graduate` skill would put about 100 tokens of description into every session in every repo and take a place in the plugin budget. A checklist in the spec was turned down because nothing reads the spec after the build.

**What starts it.** The brainstorm session writes the result on the MVP's line in `mvps.md`, and the page shows the next step: open a session in the named repo and say `graduate` or `stop`. Abdul starts that session when he is ready. A client's site that graduates at delivery starts the same way, with no brainstorm session. No scheduled task or pending entry starts it, because the page already names the step.

**Graduation, in order.** The session ticks each step in a graduation section of the brief, so a second session carries on from the first unticked step if one session is not enough.

1. The graduation line in the brief: date, named person, reason and, if needed, the neutral name.
2. The pre-launch gate. If a step fails, the app is still an MVP on test data, so the same session fixes it under fast-lane rules and runs the gate again.
3. The core design, `docs/design.md`: screens with their routes, patterns, modules.
4. A check per pattern, the import rules, and the screenshot test with its baselines.
5. The port column, for a stack other than Next.js.
6. The lane block in `CLAUDE.md`: "Lane: careful", the suite budget and the "Production" line.
7. The git hooks: `pre-push`, and the note check that "Where the note check lives, and baselines for changed screens" decides.
8. The host's Git link and `migrate:production`.
9. Staging, with seed data only, if the product needs it.
10. Abdul's steps in `~/.claude/pending.md`: the real environment variables, the domain and approval of the new baselines. These touch production, so no agent does them.
11. The MVP's line in `mvps.md`, and the README entry.

During stage one a client's site runs steps 1, 2 and 6 to 11. Steps 3 to 5 wait for stage two, as "How an MVP's limits and its end are recorded" decided.

**Stopping.** The session marks the line `stopped`, makes any last commit, then archives the repo with `gh repo archive` once Abdul says yes in that session. Archiving comes last because it makes the repo read-only. Abdul's steps go to `~/.claude/pending.md` as numbered actions with the provider's current button names: pause or remove the hosting, since the CLI asks him to type the project name; revoke the keys; and, for a product, delete or return its real data, since no agent touches production.

**A product named after its client.** The README lists it under a neutral name that says what it is, such as "a kit-ordering site for a football club". The graduation session proposes the name and Abdul approves it. The `commit-msg` hook stays as it is. Keeping client work out of the products section was turned down because it hides real work from the reader the README is for, and an exception in the hook for a willing client was turned down because the hook would then need a list of exceptions.

**Orderflow at the switch.** A fifth switch session runs steps 3 and 4 on Orderflow. The four sources "What happens to Orderflow" names hold no screen list and no module map, so the screens come from the route tree (29 `page.tsx` files today), the modules from the folders under `src/` (`app`, `controls`, `lib`, `model`, `styles`) and the boundary checks Orderflow already has, and the patterns from `docs/patterns.md`. The baselines come from the local app on seed data with a fixed clock, not from the live app: real orders change daily, so a baseline from the live app would fail the next day and would put customer data in git. When stage two lands the kit site gets the same session.

**Procurement.** The switch writes nothing for its core design. The revamp's first session runs steps 3 and 4, since the revamp rewrites the design anyway.

`CONTEXT.md` now defines neutral name.

Changed by "Where the note check lives, and baselines for changed screens" (2026-11-01): step 7 commits `.githooks/` (`pre-commit`, `pre-merge-commit`, `pre-push`), sets `core.hooksPath` and `branch.main.mergeoptions=--no-ff`, and adds a `prepare` script that sets both again. The fifth switch session also runs step 7 on Orderflow; this is a default.
