Status: resolved
Assignee: Abdul (wayfinder session 2026-10-27)
Type: grilling
Blocked by: 02, 13

# What the fast lane does, from brief to done

## Question

What are the fast lane's steps from an idea to a deployed app Abdul calls done? Pin down what the one-page brief holds and who writes it, whether one session builds the first version or several, how the build is checked against the brief, and the done test (for example: a public URL, the main flow works end to end, Abdul has used it once). Also decide which of today's rules still hold in this lane; no secrets in code and Abdul approving each push are the likely survivors.

## Answer

The fast lane takes an idea to an MVP: the smallest live app that runs the main flow end to end, on test data only. It may build any feature, payments and sign-in included, but nothing real goes through it. Real means real customers, their data, money that moves, or live keys. Stripe test mode and test accounts are fine. The step from test to real is graduation, and that is where the pre-launch gate runs, since the gate's own trigger is "real users or real data".

The steps:

1. Claude interviews Abdul and writes the brief. It fits on one page and holds six things: the problem and who has it, the main flow in a few steps, a link to the approved prototype and its screenshots, what the MVP leaves out, the done checks the agent can run, and what stays test-only. A brief that runs past a page means the MVP is too big.
2. Every MVP starts with a prototype, built in the app's real stack with fake data. Abdul reacts to it in a session and approves it. The approved prototype becomes the first commit, and Claude screenshots each screen.
3. One build session in auto mode, with `/goal` set to the done checks, builds the MVP on top of the prototype code. If the context fills, a fresh session carries on from the brief and the git log. No issue files.
4. Checks while building: tests and typecheck after each small feature, a browser pass through the main flow at the end, and one `/code-review` in a fresh context against the brief.
5. Done means four things: live at a public URL, the browser pass completes the main flow, Abdul approves a side-by-side page of prototype and MVP screenshots with each difference marked, and Abdul has used it once.

Limits: one day for the prototype, three days for the MVP from the prototype's approval. At each limit Abdul cuts scope, carries on or stops. A main flow too big for one build session gets cut, never split across sessions, because many sessions each making their own design choices is the drift this lane exists to stop. Each MVP gets its own private repo, so the public repo only ever shows products.

Rules that hold in this lane: no live keys or secrets in code, enforced as a hard deny rather than a reminder; Abdul approves each push; the code rules skill loads for every code session. Issue files, harden-issues, the review and verify gates, the decisions queue and the daily brief do not apply here.

The terms prototype, MVP, product, brief, fast lane, careful lane and real are now in `CONTEXT.md`. "Experiment" is retired.

Two concerns Abdul raised went elsewhere on the map: keeping careful-lane slices aligned to the MVP's core design, and which steering files each lane loads.

Changed by "What the verifier checks in the browser" (2026-11-01): the side-by-side page marks each screen that the prototype did not have as "new".

Changed by "How an MVP's limits and its end are recorded" (2026-11-01): the one-day, three-day and one-page limits are gone. The prototype holds all of the look and behaviour, and the build session adds only what fake data cannot do. A `site` runs the shared `site-checks` set, and the brief lists only its own checks. The person the MVP is for approves the prototype and the side-by-side page.

Changed by "How every version 2 session stays under 300k tokens" (2026-11-02): the build session compacts at about 367k under a 400k window and carries on. A fresh session from the brief and the git log is now for a session that stopped, not one that filled.
