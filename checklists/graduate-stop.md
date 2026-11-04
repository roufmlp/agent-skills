# Graduate or stop

When Abdul says `graduate` or `stop` in a product's repo, follow this file. Read the product's `CLAUDE.md` and `BRIEF.md` first. Tick each step in the brief's "Graduation" section as it finishes, so a second session carries on from the first unticked step. Abdul's own steps go to `~/.claude/pending.md` under "Do", one numbered action each, with the provider's current button names taken from its current docs; they touch production, so no agent does them. The source is "How a product graduates, stops or switches over" in the workflow v2 map.

## Graduate

Graduation is Abdul's decision and it is one way. Before step 1, he names the person who will put real data into the product within a week; for a client's site that is the client, at delivery. If he cannot name one, stop here and say so.

1. **The graduation line** in `BRIEF.md`: the date, the named person, the reason and, for a product named after a client, a neutral name that says what it is ("a kit-ordering site for a football club"). Propose the name; Abdul approves it.
2. **The pre-launch gate**: the ten steps at the end of the `coderules` skill, every one, with the result of each written under the graduation line. A failing step is fixed in this session under fast-lane rules, then the gate runs again. The app is still an MVP on test data until step 6.
3. **The core design**, `docs/design.md`, from `templates/design.md` in the skills repo: screens with their routes and groups in the one table the note check and the screenshot test read, one `Shared files for <group>:` line per group, then patterns and modules. Every screen with a `page.*` file gets a row; a route left out has no baseline and no note check. Stage two.
4. **The checks**: one per pattern, the import rules, and the screenshot test with its baselines from the local app on seed data. The test is `templates/screens.spec.ts` in the skills repo copied to `e2e/screens.spec.ts`; it reads the screens table of step 3. The product writes `e2e/screens-seed.ts` beside it, which seeds the data, signs the browser in, fills each `[param]` in a route and names the one instant every screen is shot at (`time`, required; the spec fixes the browser's clock at it). A date the server renders follows the server's clock, not the browser's: the seed starts or points the local app at the same instant through the app's one ambient clock read, or masks the element. `npx playwright test e2e/screens.spec.ts --update-snapshots` takes the first baselines, and a second run with no flag must pass before they are committed. Stage two.
5. **The port column**, for a stack other than Next.js and Supabase. Stage two.
6. **The careful-lane `CLAUDE.md`**: rewrite the file in the form at the end of this page. The "Production" line is read by the `live-key-deny` hook from the moment it exists: from then on an agent in this repo cannot name the address or the database project, run `migrate:production`, pull the host's variables or deploy. Write the line last, with the Edit tool, and check the refusal once with a harmless command that names the address.
7. **The git hooks.** Four commands in the product folder, then one commit:

   ```
   cp -R ~/.claude/skills/workflow/templates/githooks .githooks
   npm pkg set scripts.prepare="sh .githooks/prepare"
   npm run prepare
   git config --get core.hooksPath
   ```

   The last line must print `.githooks`; `prepare` also sets `branch.main.mergeoptions` to `--no-ff`, so every merge into main runs the `pre-merge-commit` hook, and runs again on every `npm install`, since git does not copy local config into a clone. Commit `.githooks/` and `package.json` by name. The hooks call `~/.claude/skills/workflow/lib/note_check.py` and refuse every commit, merge and push while that file is missing; `python3 ~/.claude/skills/workflow/lib/note_check.py --help` names the checks. From this step on, a commit that touches a screen's route folder, a baseline or `docs/design.md` needs a branch that names its change note (`note/<feature>/<nn>`, `note/<nn>` or `feature/<name>`), so write the first baselines in step 4 before this step.
8. **The host's Git link and `migrate:production`.** Connect the repo to the hosting project so that only a push deploys (for Vercel, `vercel git connect` in the product folder; check `vercel git --help` first, the CLI changes). Add a `migrate:production` script that applies the migrations and writes the name of the last one it applied to a file git ignores; the `pre-push` hook of step 7 reads that file. The script is Abdul's to run; the deny hook refuses an agent's run of it.
9. **Staging**, if the product needs one: a second project at the host and a second database with seed data and test accounts only, never a copy of production.
10. **Abdul's steps**, in `~/.claude/pending.md` under "Do": the real variables on the host, the live keys, the domain, the client's inbox, and his approval of the first baselines.
11. **The records**: the product's line in `~/code/ideas/mvps.md` (status `graduated`, the date) pushed to the ideas repo, and the README entry under the neutral name, which waits for the switch.

In stage one a product runs steps 1, 2, 6, 8, 9, 10 and 11 without the README entry. Steps 3, 4, 5 and 7 wait for stage two.

## Stop

1. Mark the product's line in `~/code/ideas/mvps.md` `stopped`, with the date and the reason, and push the ideas repo.
2. Make any last commit in the product's repo. The push is Abdul's.
3. Write Abdul's steps to `~/.claude/pending.md` under "Do": pause or remove the hosting project (the CLI asks him to type its name), revoke the keys, and for a product delete or return its real data.
4. Ask Abdul, in this session, whether to archive the repo. On yes, run `gh repo archive <owner>/<repo> --yes`. This comes last because it makes the repo read-only.

## The careful-lane CLAUDE.md

```
# <Product>

Lane: careful. This file sets the rules for every session in this repo. The chain does not apply.

The brief is `BRIEF.md`. The core design is `docs/design.md`; every build session and `/code-review` read it. Change notes live in `changes/`.

Every change passes five steps: a change note; one auto-mode session with `/goal` set to the note's checks; tests and typecheck; a browser pass through the main flow; one `/code-review` in a fresh context. Before the session builds a one-note change it runs `python3 ~/.claude/skills/workflow/lib/plan_check.py notes changes/<nn>-*.md` once; a refusal stops it. A feature of several notes runs through `/build-feature <name>`. A change that touches money, authentication, secrets, a migration or row writes gets `/code-review` at `max` effort, and steps 1 to 7 of the pre-launch gate run before it reaches local main.

Suite: <npm test>
Harness suite: <npm run test:harness>
Typecheck: <npm run typecheck>
End-to-end: <npm run e2e>
Suite budget: <10> minutes
Main flow: <the flow a person takes most, in one line, and the spec that drives it>

Hosting: <Vercel>. Deploy to a test environment: `<command>`. Migrations: `<command>`. The repo is linked to the host, so only Abdul's push deploys production. Abdul runs `migrate:production` before that push; the `pre-push` hook holds the order.

Production: <address>, <database project reference>

No agent touches production. The `live-key-deny` hook reads the line above and refuses a command, read, search or fetch that names either item, a run of `migrate:production`, `vercel env pull`, `vercel --prod`, `supabase db push` and `supabase link`. Staging, where there is one: <address>, seed data only.

The MVP list is `~/code/ideas/mvps.md`. Pushes to the ideas repo need no approval; every push to this repo's origin is Abdul's call.
```

The five `Suite` to `Suite budget` lines are read by `lib/suite.py`, the one road every
build agent takes to the tests: one command each, as typed in a shell, and the budget as a
whole number of minutes. `Harness suite` is the only optional line; delete it where the
product has one suite. A missing line is a refusal, not a default. `Main flow` is read by the final verifier
of `/build-feature` for its browser pass when the product has no `BRIEF.md`.

The "Production" line holds comma-separated identifiers only, each six characters or more with no spaces: the address and the database project reference, and a host where one is unique to production. A shared host such as a regional pooler is not an identifier, because staging uses it too.
