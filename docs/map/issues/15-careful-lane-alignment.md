Status: resolved
Type: grilling
Blocked by: 08

# How the careful lane keeps every slice aligned to the core design

## Question

Once a product is in the careful lane, work lands in small slices, often in separate sessions. Today each run-issues session makes its own design choices, and the finished app drifts from the prototype and from itself. What holds every slice to the product's core design, rules and module boundaries? Candidates: a design system and module map written at graduation that every slice must read, the prototype screenshots kept as a check every slice re-runs, a check that refuses a slice adding a new pattern, or a fresh review against the core design. Decide what the core design holds, where it lives, who updates it, and what refuses drift rather than advising against it.

Changed by "What happens to Orderflow" (2026-10-31): at the switch, Orderflow's prototype screenshot pairs move out of `.scratch/` into `tests/`, so this ticket can use them as a check. Abdul also asked whether a feature the size of request-kinds, 24 issues in version 1, is one session in version 2. Under "What the careful lane keeps" it is not: a change too big for one session is cut into several change notes. Request-kinds makes a good first case for this ticket. Ten of its 24 slices carry a migration and six touch money, and every note that does gets `/code-review ultra`, a gate run and, for a migration, Abdul's approval of its direction. How a feature is cut therefore also sets how many of those checks run.

Changed by "How a regular audit keeps the workflow small" (2026-10-31): Abdul wants several agents working on one product at once, and his worry is two of them building the same thing two ways. Whatever check this ticket picks, the monthly audit counts its failures in a "Drift" row, so the check needs a result a script can count.

## Answer

Each product gets a core design at graduation, and checks refuse a change that drifts from it. The core design is one page, `docs/design.md`, with three parts: screens, patterns and modules. Domain words stay in the product's `CONTEXT.md`. A change either follows the core design or changes it on purpose, with Abdul's approval recorded in its change note.

Orderflow is the evidence. It holds about 100 checks that refuse, but most of its "one component" checks arrived after the drift they fix: the six `one-*` tests landed between 18 September and 15 October, after a UI audit on 25 September found 126 faults on 18 pages, six row shapes for one list among them. Its fidelity tool produced 2,175 difference rows across 290 screens and never blocked an issue, and 8 of 16 gate rejects after 4 October were screen differences found by eye. Its own rulebook names the cause: the prototype code sat on branches that never merged. In version 2 the prototype is the first commit, so that cause has gone, and the checks get written before the drift instead of after it. The findings, with commits and paths, are in [the drift research](../research/15-orderflow-drift.md).

**When.** The graduation session writes the core design from the MVP's code and the approved prototype, along with its checks and screenshot baselines, after the pre-launch gate passes. An MVP builds in one session and does not drift, and one that stops never needs a core design.

**What refuses drift.** Three checks, each tied to one part of the core design:

1. Screens. A Playwright `toHaveScreenshot` test captures every main-flow screen at 390 and 1280 pixels, and any difference fails. Orderflow turned pixel comparison down because it compared plain HTML prototypes with a different stack. Here the baseline is the product itself, in the same stack. The test runs on every baseline screen, whatever the note names, because a change to a shared button can move a screen nobody mentioned. It runs in the build session on Abdul's laptop only, since Playwright keeps a baseline per operating system and CI runs Linux; Docker baselines would add a container to every product for a check the build session already runs.
2. Patterns. Each pattern in the core design names a check that refuses a second way of doing it, and an entry without a check is not approved. Orderflow's lint ban on raw controls outside `src/controls/` is the starting kit.
3. Modules. ESLint's built-in `no-restricted-imports`, written from the modules part. A custom test is kept for a rule ESLint cannot express, such as Orderflow's "browser code never reaches the database".

`/code-review` also reads the core design, but only the checks refuse. The pattern and module checks run in the "tests and typecheck" lane step and the screenshot test in the browser pass, so no lane step is added. Each check prints one fixed line when it fails, for example `DRIFT: pattern one-button`, and the weekly script counts those lines for the audit's Drift row.

**What it costs.** Orderflow's 12 pattern and boundary checks ran in 10 seconds on 31 October, and an ESLint import rule adds under a second to lint. The screenshot test is an estimate, not a measurement: the browser pass already opens each screen, so a capture adds a second or two, about a minute for 15 screens at two widths. Against 69 minutes of run time per version 1 issue that is under 3%. The real costs are the graduation session that writes the checks, about one session per product, and screenshot failures that are not drift (fonts, animations, the date), which `animations: 'disabled'`, a fixed clock and masks mostly stop.

**Changing the core design.** A change note that needs a new pattern or module says so in a line, "Core design: adds ..." or "Core design: rewrites ...", and Abdul approves it in the interview, where he already is. A session that meets an unapproved new pattern mid-build stops that part and lists it in its end report. There is no scheduled review: every entry names a check, so an entry that no longer fits fails, and the session follows it or a note changes it. If one check fails again and again in the Drift row, the audit proposes to revisit that entry.

**Big changes.** A full redesign, a move from one tenant to many or a new database rewrites part of the core design. A redesign starts as the fast lane does, with a prototype in the real stack that Abdul approves. The first note rewrites the core design, its checks and its baselines, and the notes after it follow the new version. A tenancy or database change starts with a note that rewrites the modules part and its import rules, and it needs no prototype unless the screens change. It touches migrations, so it also gets `/code-review ultra`, the pre-launch gate and Abdul's approval of the migration's direction. Changing the design note by note was ruled out, because many sessions each deciding the new design is the drift.

Abdul asked that the big-change steps cannot be missed, so a note check refuses a commit in three cases:

1. A screenshot baseline changes and the change note does not name that screen.
2. `docs/design.md` changes and the note has no "Core design:" line with Abdul's approval.
3. The note rewrites the screens part and links no approved prototype.

A redesign started without a prototype fails at its first changed screen, and a tenancy change fails when it touches the module rules without its rewrite line. The note check is the same small script that guards the baselines, so no new tool arrives.

**Parallel notes.** When Claude cuts a feature into notes and two of them need the same new pattern, it gives the pattern to one note and the others wait for it. How a note waits belongs to "How a feature with several change notes runs without Abdul".

**Orderflow.** At the switch the brief session also writes Orderflow's core design from `docs/patterns.md`, `docs/visual-direction.md` and its two ADRs. Orderflow keeps its existing checks, takes its screenshot baseline from the live app that day, and leaves the 290 prototype pair folders (317 MB) and the fidelity tool at the `v1` tag rather than moving them into `tests/`.

**Handed on.** The full test suite is a separate question: Orderflow's config puts `npm test` at about 197 seconds on 8 workers, and Abdul sees about ten minutes per issue once reruns and flaky tests are counted. It went to two new tickets, "How long Orderflow's test suite takes, and where it flakes" and "How the careful lane keeps the test suite fast and trusted". Two of Orderflow's 83 check files failed on 31 October, `turbopack-trace` among them; both test the production build, not drift, and this ticket leaves them.

`CONTEXT.md` now defines core design.

Changed by "How a feature with several change notes runs without Abdul" (2026-10-31): a note waits through a "Waits for:" line, and the runner starts it only once every note it names has merged into the feature branch. A final reviewer now reads the whole feature diff against the core design after the last note merges.

Changed by "Whether the build agents work test-first" (2026-11-01): for a one-note change, the note check hook also runs the red check before the change merges to local main. The seams that `/tdd` tests at come from the modules part of the core design.

Changed by "What the verifier checks in the browser" (2026-11-01): every screen in the screens part has a baseline, not only the main-flow screens. A screen added after graduation takes its first screenshot as its baseline, committed with the feature, and Abdul approves it before the push. A new screen needs a prototype only when it needs a new pattern. The screens part names each screen's route, and the note check also refuses a diff that touches a route its note's "Screens:" line does not name.

Changed by "How a product graduates, stops or switches over" (2026-11-01): the baselines are taken from the local app on seed data with a fixed clock, never from a live app with real data, which changes daily and would put customer data in git. Orderflow's core design is written by a fifth switch session, not the brief session.

Changed by "Where the note check lives, and baselines for changed screens" (2026-11-01): the note check is a git hook in each graduated repo, calling one plugin script, and maps each commit to its note by branch name. Case 1 counts a baseline as named when any merged note of the feature names its screen, because the final verifier retakes changed baselines on the merged branch.
