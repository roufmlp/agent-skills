Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: grilling
Blocked by: 25

# Whether version 2 is built in two stages

## Question

The map plans one build and one switch: version 2 is built whole, then everything moves on one day. [The walkthrough](../research/25-walkthrough.md) found a second road. Build the fast lane first, use it on one real MVP, and only then build `/build-feature` and the careful lane.

For: the fast lane is a small part of version 2, and eight of its ten open gaps sit in steps one real MVP would meet. The kit site already runs a fast lane under version 1 and has broken two of its limits. The careful lane's thirteen gaps can be grilled on paper while stage one runs.

Against: Orderflow and procurement stay on version 1 until the careful lane exists, with its 33 hooks and an evening check that starts fixes on its own, on the one product that holds real orders. An MVP that graduates in stage one has nowhere to go. Two sets of global rules are in force at once.

Decide one stage or two. If two, say what stage one holds, what ends it, and what happens to an MVP that is ready to graduate before stage two lands.

The simpler build is two stages, since stage one is small. The simpler rule set is one stage, since only one set is ever in force. Say which simplicity matters more, and what the other costs.

## Answer

Version 2 is built in two stages, and no development waits for either. Stage one is the fast lane. Stage two is `/build-feature` and the careful lane, and the switch happens when stage two is built.

**State on the day.** Request-kinds was on its last issues, with issues 01 to 24 due to finish within the hour, and its loop of carves, findings, register rows and queue items still to run. The kit site was finishing its prototype. Abdul plans two or three new Orderflow features and multitenancy, to sell it to 1,000 customers within six months. Multitenancy touches sign-in rules, row policies and migrations, three of the five risk classes, so it belongs in the careful lane.

**Why two.** The simpler build beat the simpler rule set. One stage would not remove the overlap, because Orderflow keeps version 1 until Abdul says request-kinds is finished on either road. Two stages give the fast lane a real test before the careful lane is built on it, and give the careful lane's thirteen gaps, the ones that can cost a real business money or data, more time on paper. The price is one line in the global `CLAUDE.md` and a longer overlap. The line says that a repo whose `CLAUDE.md` reads `Lane: fast` follows that file, not the chain or the pre-launch gate. Without it, version 1's global file would send every MVP session down the chain and gate every MVP deploy.

**Stage one holds** the ideas repo, the brainstorm routine and its prompt, the brief and `CLAUDE.md` templates, the code and design rules skills, the live-key deny, the side-by-side page and that one global line. The careful-lane half of "How a change goes live" (the pre-launch gate inside a run and production migrations) moves to stage two. Stage one ends when the three fast-lane tickets are resolved ("How the ideas repo and the brainstorm routine run", "How an MVP's limits and its end are recorded" and the fast-lane half of "How a change goes live") and one MVP is live with Abdul's "done" or "stop".

**Nothing waits.** The kit site MVP build starts when Abdul approves the prototype, without the stage-one tools. It tests the fast-lane steps (brief, prototype, one build session, done) on a real client's site; the new tools get their first test on the next MVP. Orderflow stays on version 1 until stage two lands, and its smaller features run on the chain meanwhile. Each risk-class issue they open is one more item for the switch sweep, which is why multitenancy does not go on version 1: nearly all of it touches a risk class, and it would swell the sweep. Abdul holds back one small feature as the careful lane's first real test. The multitenant design is grilled on paper now, and its build starts in the careful lane after that first feature.

**The evening check sorts now.** The 18:00 Orderflow job stops starting fixes as a version 1 action, before the switch, the same kind of action as pausing procurement on 31 October. Two stages make the overlap longer, and with many tenants a fix started on its own could touch other customers' data. Each fix now waits until Abdul asks for it.

**The switch does not need a clean backlog.** It still needs only what "What happens to Orderflow" set: version 2 built, Abdul's word that request-kinds is finished (no bug blocks a pilot user) and no run in progress. The sweep turns the open risk-class items that still hold into draft change notes, open request-kinds issues among them. Every other issue and queue item stays readable at the `v1` tag.

**Graduation waits for stage two.** An MVP ready to graduate in stage one stays at keep, and the one-keep limit does not count against it while stage two is the only thing it waits for. The brainstorm page lists it as "waiting for the careful lane", and it graduates at the first session after stage two lands. Graduating at any time, which "What moves an MVP to the careful lane" allows, also waits until then.

**What one stage would have cost.** No fast-lane evidence before the bigger lane is built, and a first careful-lane feature that would also be the first real use of everything in version 2.

`CONTEXT.md` now defines build stage and says when the switch happens.

Changed by "How an MVP's limits and its end are recorded" (2026-11-01): the kit site waits for the stage-one tools instead of building on version 1, and graduates at delivery once the pre-launch gate passes. No MVP graduates before stage two except one a waiting client needs. The "waiting for the careful lane" exception is gone, since keep has no limit.
