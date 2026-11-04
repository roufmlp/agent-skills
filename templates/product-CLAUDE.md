# <Product>

Lane: fast. This file sets the rules for every session in this repo. The chain and the pre-launch gate do not apply until graduation, which rewrites this file.

The brief is `BRIEF.md`. Rulings from the prototype review are in `prototype/decisions.md`. There is no core design until graduation writes `docs/design.md`.

Nothing real goes through this MVP: no real customers or their data, no money that moves, no live keys. `.env.local` holds test values only, and Abdul adds a key there only when the provider needs his login to issue it.

The build runs as one auto-mode session with `/goal` set to the brief's done checks. It adds only what fake data cannot do: email, real content, storage and the deploy. It does not design again. After each small feature it runs the tests and the typecheck. At the end it runs `site-checks` for a site, a browser pass through the main flow, one `/code-review` in a fresh context against the brief, and writes the side-by-side page of prototype and MVP screenshots with `lib/side_by_side.py` in the skills repo (`write`, fill in every difference, then `check`).

Hosting: <Vercel>. Deploy to a test environment: `<command>`. Migrations: `<command, or "none">`. The project has no Git link until graduation; the session deploys from local main whenever a done check needs the live site. A deploy to a test environment is not a push.

The MVP list is `~/code/ideas/mvps.md`. The session that deploys writes the live date on this product's line and pushes. Pushes to the ideas repo need no approval; every push to this repo's origin is Abdul's call.

When Abdul says graduate or stop, follow `checklists/graduate-stop.md` in the workflow plugin.
