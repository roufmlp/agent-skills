Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: grilling
Blocked by: 25

# How a change goes live

## Question

Every lane step so far ends at Abdul's push. [The walkthrough](../research/25-walkthrough.md) found that what happens around the push is undecided in both lanes, gaps F8, C12 and C13.

In the fast lane, done needs "live at a public URL", but no ticket says who creates the hosting project and sets its test variables, whether a deploy counts as a push, or whether an unattended build session may deploy. A done check that needs the live site stalls `/goal` until this is settled. In the careful lane, "an agent runs steps 1 to 7 of the pre-launch gate on the feature branch" before the push, but none of `/build-feature`'s roles owns it, and it has no place before or after the merge to local main. Step 1 last ran against production, where the new migrations do not exist yet. And no ticket says who applies migrations to production, when, or that they go in before the push that deploys the code. That is the step a deploy cannot roll back. Version 1 put it on Abdul, and its gate caught an order fault on migration 0077.

Decide who deploys in each lane, which role runs the gate and where it sits in the run, and who applies production migrations and in what order against the push.

The lighter option: the fast-lane agent deploys a test-only MVP itself, since nothing real moves; the final verifier runs gate steps 1 to 7 before the merge to local main; Abdul applies migrations before his push, from a line in the feature report. A heavier answer says what this would cost.

Changed by "Whether version 2 is built in two stages" (2026-11-01): the fast-lane half of this ticket (F8) belongs to stage one, and the careful-lane half (C12 and C13) to stage two. They may be resolved apart. The kit site MVP build meets F8 first.

Changed by "How an MVP's limits and its end are recorded" (2026-11-01): the session that deploys writes the live date to `mvps.md`. The kit site waits for the stage-one tools, so it is the first MVP to go live on version 2.

## Answer

No agent touches production. An agent deploys MVPs, previews and staging itself; Abdul alone applies production migrations and pushes, and two refusals hold the line rather than a rule an agent must remember. He accepted each point below on 2026-11-01.

**Production.** The environment where a product's real users and real data live. An MVP has none: previews, staging, QA and an MVP's live address are test environments, whatever the host calls them. When an MVP graduates its address becomes production, and from that day no agent deploys it.

**The host belongs to the repo.** Abdul may host one product on Vercel and the next somewhere else, so no rule names a host. Each product's `CLAUDE.md` carries a "Hosting" block of three lines: the host, the command that deploys to a test environment, and the command that applies migrations. The template starts with Vercel and Supabase. The port list gets no hosting row.

**The fast lane deploys itself (stage one).** The build session creates the MVP's hosting with the host's CLI and sets its variables from `.env.local`, which holds test values only. Abdul adds a key there only when the provider needs his login to issue it. The project has no Git link and the session deploys from local main whenever a done check needs the live site, so `/goal` never waits on him. A deploy to a test environment is not a push; his push to origin stays his. The kit site's prototype already went live this way on 1 November. Graduation adds the Git link, after which only his push deploys.

**Who runs the gate (stage two).** Steps 1 to 7 of the pre-launch gate run on every careful-lane change, before the merge to local main: the final verifier runs them for a feature, the note's verifier for a one-note change. A failed step is a final-check finding and goes into the one fix round, so nothing reaches main unchecked. Running it on every change rather than only on risk-class changes costs some minutes a run, which the audit will measure; the risk-class-only road would miss a change that breaks row rules and nobody marked as such.

**Where it runs.** On staging when the repo names one, otherwise locally. On staging the verifier first applies the feature's migrations, which rehearses them before production gets them, then runs steps 1, 3, 4, 6 and 7 on a deploy of the feature branch. Staging holds seed data and test accounts only; a copy of production data would make it production. A preview is allowed only when its variables point to a database that is not production. Abdul set up staging for Orderflow on 1 November, for his own testing.

**Migrations go first.** The order before a push never changes: the "Do" items, then the migrations, then the push. To keep that order safe, a migration may only add. A drop or a rename goes in a later change, once the code that stopped using it is live, and the final reviewer refuses a migration that breaks the code on `origin/main`.

**Abdul applies them, and a hook enforces the order.** He runs `migrate:production` in his own terminal. On success it writes the name of the last migration it applied to a file git ignores. A `pre-push` hook in the product repo reads only that file and refuses a push to `main` that carries a later migration. It never connects to a database. It installs the way the note check does, which "Where the note check lives, and baselines for changed screens" decides.

**What keeps agents out.** Abdul keeps production secrets in his Mac's keychain, not in files. That covers the database password but not the CLI logins: the Supabase CLI reads its keychain token without a prompt, and the Vercel CLI token sits in a plain file, `~/Library/Application Support/com.vercel.cli/auth.json`. Either one reaches production, and `vercel env pull` would hand an agent Orderflow's database URL. So the live-key hard deny hook also refuses any agent command or file read that names an identifier from the repo's "Production" line (database host, Supabase project reference, production domain), refuses `migrate:production`, and refuses `vercel env pull` and `vercel deploy --prod` in a graduated repo. Agents keep both logins for test environments and MVPs. Stage one builds this refusal, because Orderflow is live today and the kit site graduates at delivery; that timing is a default, not a ruling.

**Turned down.** An agent applying production migrations: nothing it gains is worth a production credential on the machine. A `pre-push` hook that reads production's migration list: it needs a credential an agent could find. A release script alone: Abdul can type `git push` around it. A line in the feature report alone: it refuses nothing. The keychain alone: the CLI logins go around it.

`CONTEXT.md` now defines production.

Changed by "Where the note check lives, and baselines for changed screens" (2026-11-01): the `pre-push` hook is committed in the product's `.githooks/` and calls the plugin script; graduation step 7 and a `prepare` script install it.
