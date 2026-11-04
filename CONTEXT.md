# Workflow

How Abdul takes an idea to something people use, with Claude Code doing the building.

## Language

### Stages of an idea

**Prototype**:
A look-and-behave version of an idea, with fake data and no backend, built in the app's real stack so it can become the MVP's first commit.
_Avoid_: Mockup, demo, experiment

**MVP**:
The smallest live app that runs the main flow from start to end, on test data only.
_Avoid_: Experiment, first version, v1

**Product**:
An app that real users or real money go through.
_Avoid_: Experiment, live app

**Brief**:
The document that defines an MVP or a product: the problem, the main flow, the approved prototype, what is left out, the done checks and what stays test-only.
_Avoid_: Spec, PRD, SPEC.md

### Lanes

**Fast lane**:
The way a prototype becomes an MVP. It may build any feature, but nothing real goes through it.
_Avoid_: Experiment lane

**Careful lane**:
The way a product is built and changed once something real goes through it.

**Real**:
Real customers, their data, money that moves, or live keys. Abdul's own data counts as real. A customer's business data in a pilot counts as real from the first day, even if nothing has left the app. Payments in test mode and test accounts are not real.

**Production**:
The environment where a product's real users and real data live. An MVP has none. Previews, staging, QA and an MVP's live address are test environments, whatever the host calls them.
_Avoid_: Live, prod (for a test environment the host labels production)

**Graduation**:
The one-way step that makes an MVP a product, taken before anything real goes through it. Only Abdul graduates an app.
_Avoid_: Promotion, launch

**Stopped**:
A product or MVP that ends: its real data is deleted or returned, its keys are revoked and its repo is archived. A stopped product never becomes an MVP again.
_Avoid_: Retired (skills and hooks retire to the version 1 record), killed, archived

**Parked**:
A product with no work under way until the brainstorm session picks it again.

**Change note**:
The half page that defines one change to a product: what changes and why, the screens or flow it touches, the done checks and the risk classes it touches. It is written for the build agent, after the writer reads the code the change touches.
_Avoid_: Issue, ticket, slice

**Feature**:
A change too big for one session, cut into change notes that run as one group. A change of one note is not a feature.
_Avoid_: Epic, change set, batch

**Interview**:
The conversation in which Claude cuts a feature into change notes, writes each note's done-check tests and asks Abdul the questions that could stop the run. It ends when he approves the feature plan.
_Avoid_: Planning session, grilling, kickoff

**Feature plan**:
The one page Abdul approves before a feature runs: a line per note, the order, which notes wait for which, and the questions of four kinds. The run starts only from an approved plan.
_Avoid_: Approval page, one-pager

**Cut**:
A change note taken out of a feature in the interview that follows a failed note, merged or not. It returns later as a one-note change or in another feature.
_Avoid_: Carve, drop, descope

**Done check**:
A command or test that passes only when the change works. It fails on the code as it stands before the change, and the build agent runs it.
_Avoid_: Acceptance criterion, criteria

**Flake**:
A test failure that passes when its file runs again alone on the same code.
_Avoid_: Flaky run, intermittent failure

**Red check**:
The check that each new test fails on the code from before the change. A test that passes there proves nothing. A test named `keeps:` protects behaviour the change does not touch, and the check skips it. The change's migrations count as code from the change, so the code from before it has none of them.
_Avoid_: Test-first check, mutation test, red-before-green

**Hostile walk**:
The verifier's pass through a change note's new and changed actions in the running app, with throwaway cases that try to break them: a reload, a second road, two fast clicks, the narrow width, the empty and error states. A case that finds a fault becomes a spec in the fix.
_Avoid_: Browser walk, acceptance walk, manual QA

**Note check**:
The check that refuses a commit which goes past its change note: a screen, a baseline or a core-design change the note does not name. The branch a commit sits on names its note.
_Avoid_: Diff check, scope guard

**Baseline**:
The approved screenshot of one screen at each width, which the screenshot test compares against. A change that alters a screen on purpose names it, the final check takes the new baseline, and Abdul approves new and changed baselines with his push.
_Avoid_: Snapshot, golden image

**Port list**:
The table in the spec that names each tool slot the careful lane uses, its Next.js and Supabase value, and the place in the plugin that uses it. A new stack fills a new column when its first MVP graduates.
_Avoid_: Stack slots, stack config, adapter

**Suite budget**:
The longest a product's full test suite may take. A reading over it puts a choice to Abdul at the next feature interview: raise the budget or prune the tests.

**Lane step**:
A step every change in a lane passes before it is done.

**Toolbox**:
The skills any session in either lane uses when it needs one. A tool is never a lane step.

**Core design**:
The one page that fixes a product's screens, patterns and modules, written at graduation. Every change follows it or changes it on purpose, with Abdul's approval in the change note.
_Avoid_: Design system, style guide, architecture doc

**Risk class**:
One of five kinds of change that get stricter checks in the careful lane: money, authentication, secrets, migrations and writes to rows.
Authentication covers who may sign in and who may read or write which data, so rights rows and row policies count.

**Pending file**:
The one private list of what waits on Abdul, under two headings: actions to do and decisions to make. A decision lands there only when its default is hard to undo or the choice is his.
_Avoid_: Decisions queue, pending-on-abdul

### Choosing what to build

**Brainstorm session**:
The session, twice a month, where Abdul gives each open MVP a result and picks at most one idea to become the next MVP.
_Avoid_: Planning session, retro

**Idea log**:
The private record of every idea, its status and the reason for each "no", kept so the brainstorm session never proposes the same idea twice without a new reason.
_Avoid_: Backlog, idea list

**MVP list**:
The private list of every MVP, one line each, from the day its brief is first written until it graduates or stops. A client's site is on it like any idea. Each line names its type, site or app, and who it is for: the person who approves the prototype and accepts done.
_Avoid_: Client job, job list, project list

**Brainstorm page**:
The one page the routine prepares before each brainstorm session: open MVPs first, then the idea shortlist. It counts as opened once the session first replies to Abdul; an unopened page is updated by the next run, not replaced.
_Avoid_: Agenda, report

**Audit**:
The monthly table, linked from the brainstorm page, that measures the workflow against last month and version 1, and proposes cuts for Abdul to accept or refuse. It never removes anything itself.
_Avoid_: Review, retro, health check

**Interruption**:
Thirty minutes or more in which nothing in an unfinished session writes: not the main session, not a subagent, not a running command.
_Avoid_: Stall, idle time

### Publishing

**Public repository**:
The one repository that holds the workflow: its skills, hooks, spec and maps. Everything in it is public as it stands, and nothing is copied or scrubbed on the way out.
_Avoid_: Public pack, mirror, live repo

**Private name**:
The name of a client, meaning a person or business a product is built for, or a client's email domain. A private name never appears in the public repository. A product's own name is not a private name.
_Avoid_: Secret (a secret is a key or token), confidential name

**Neutral name**:
The name a product carries in public when its own name holds a private name. It says what the product is, such as "a kit-ordering site for a football club".
_Avoid_: Code name, alias

**Version 1 record**:
The first workflow as it stood on the day of the switch: its skills, hooks, agents and run history. Nothing in it runs and nothing in it is deleted, so it can be restored in full.
_Avoid_: Archive, legacy, old workflow

**Switch**:
The one step that moves Abdul's setup from version 1 to version 2 and freezes version 1 as the version 1 record. It happens once stage two is built. A product built on version 1 switches with it: it gets a brief, and its run history goes into the version 1 record. Going back is a rollback, not a switch.
_Avoid_: Migration (a migration is a database change), cutover

**Build stage**:
One of the two steps in which version 2 is built. Stage one is the fast lane, used beside version 1; stage two is the careful lane, and the switch follows it. Not a stage of an idea.
_Avoid_: Phase, milestone

**Release**:
A state of the public repository that Abdul declares ready. Friends and Abdul's work machine install only the latest release; work pushed between releases reaches no other machine.
_Avoid_: Version (version 1 and version 2 name the workflow), publish

**Working copy**:
Abdul's own clone of the public repository, which his sessions load directly. A change is live for him once merged, before any release.
_Avoid_: Dev copy, local install
