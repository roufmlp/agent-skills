Status: resolved
Assignee: Abdul (wayfinder session 2026-10-27)
Type: grilling

# What moves an MVP to the careful lane

## Question

What test decides that an MVP graduates? Graduation is the step from test to real: real customers, their data, money that moves, or live keys (see "What the fast lane does, from brief to done"). Candidates: Abdul using it himself for a set period, a count of real users, someone willing to pay, or Abdul's call alone. Also decide who runs the test and when, what happens to an MVP that fails it (kept private, deleted or archived), and whether an app may skip the fast lane and start in the careful one.

## Answer

An MVP graduates when Abdul can name a person who will put real data into it within a week. He can be that person himself. Nothing else counts, and only Abdul decides; the agent never graduates an app. The brief gets one line recording the date, the person and the reason.

A test that measures use cannot work here. An MVP runs on test data, so it has no real users or real money until it graduates, and Abdul's own data counts as real too. Counting users, waiting for payment or having Abdul use it for a month would all need graduation first. The test has to look forward, and a named person costs one line. Asking for someone willing to pay was stronger but ruled out products Abdul builds for himself, and free ones.

When: the brainstorm session is the fixed check. It lists every MVP that is not yet a product, and Abdul gives each one of three results: graduate, keep or stop. Keep is allowed once. At the next session the MVP graduates or stops, so old MVPs do not pile up as live deploys that cost money and can draw real users by accident. Abdul can also graduate an MVP at any time, so a waiting user never waits a month.

Stop means the live deploy comes down and the MVP's private repo is archived on GitHub. Archiving keeps the history for nothing; deleting saves nothing.

Graduation itself is one step: the pre-launch gate in the code rules runs and passes, then the first real thing goes in. The gate already triggers on "real users or real data", so this is where it belongs. No extra hardening session comes first. The careful lane starts with the first change after graduation, and "What the careful lane keeps" decides what that process is.

Graduation is one way. A product that stops is retired: its real data is deleted or returned, its keys are revoked and its repo is archived. It never goes back to being an MVP.

No app skips the fast lane. A new app that must hold real data from the first day still goes through a prototype and an MVP on test data, then graduates the day the MVP is done. That costs a few days and keeps the design aligned, which is the fast lane's reason for being. Changes to an existing product are careful-lane work.

`CONTEXT.md` now defines graduation and retired, and says Abdul's own data is real.

Changed by "How the careful lane keeps every slice aligned to the core design" (2026-10-31): the graduation session now does one more job after the pre-launch gate passes: it writes the core design, `docs/design.md`, from the MVP code and the approved prototype, with a check for each pattern, the module import rules and a screenshot baseline of every main-flow screen.

Changed by "How a feature with several change notes runs without Abdul" (2026-10-31): the glossary now calls a product that ends "stopped", not "retired", because skills and hooks also retire to the version 1 record. The meaning is unchanged.

Changed by "Whether version 2 is built in two stages" (2026-11-01): until stage two is built, no MVP graduates, at a session or at any other time. An MVP ready to graduate stays at keep, the one-keep limit does not count against it, and it graduates at the first session after stage two lands.

Changed by "How an MVP's limits and its end are recorded" (2026-11-01): keep has no limit, and the "waiting for the careful lane" exception is gone with it. A client's site graduates at delivery, since the client is the named person; one that a waiting client needs may graduate before stage two.
