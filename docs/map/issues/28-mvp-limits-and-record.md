Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: grilling
Blocked by: 25

# How an MVP's limits and its end are recorded

## Question

"What the fast lane does" sets the limits (a one-page brief, one day for the prototype, three days for the MVP) and the done test. "What moves an MVP to the careful lane" gives every open MVP a result at each brainstorm session. [The walkthrough](../research/25-walkthrough.md) found three gaps in between, F5, F6 and F10.

No ticket says when an MVP joins the list or from when its age counts. Nor does one say whether an MVP still in its prototype at the next session must take graduate, keep or stop and spend its one keep. The "done" line needs Abdul's word that he used the app, often after the build session has ended, and no session is placed to write it. Nothing checks the limits either. The kit site's brief runs to about two and a half pages with 12 done checks, and its prototype has been under review for five days. Under "refuse, or state a fact", a limit nothing checks is a reminder. Last, the side-by-side page of prototype and MVP has no tool, and "difference" means nothing when fake data meets test data. Orderflow's fidelity tool produced 2,175 difference rows that never blocked anything.

Decide when an MVP enters the list and what an unfinished one owes the session, who records done, whether the limits get a check or are dropped, and who marks the differences on the side-by-side page.

The lighter option: an MVP enters at the pick; an unfinished one gets keep or stop; the brainstorm page compares the list's dates with the limits and asks; the build agent marks the differences it judges unintended. A heavier answer says what this would cost.

Changed by "Whether version 2 is built in two stages" (2026-11-01): this ticket is part of stage one, the fast lane, and stage one ends only when it is resolved. An MVP waiting only for stage two stays at keep without spending its one keep, and the brainstorm page lists it as "waiting for the careful lane".

Changed by "How the ideas repo and the brainstorm routine run" (2026-11-01): the MVP list is `mvps.md` in the ideas repo, one line per MVP with at least its repo, idea date, live date, age, keep count and result. This ticket settles the exact fields. Build sessions write to it from `~/code/ideas` and push without asking.

## Answer

Every piece of fast-lane work is one line on the MVP list, whether it came from an idea or from a client. Two fields on the line change what happens: its type, `site` or `app`, and who it is for. Abdul turned down a separate category for client work, because the rules should follow the kind of product, not who pays for it. He accepted each point below on 2026-11-01.

**The line.** `mvps.md` holds one line per MVP: name, repo, type, for, start date, live date, done date and result. A line starts the day its brief is first written, at the pick for an idea and at the request for a client, and its age counts from that date. "For" names the person who approves the prototype and accepts done: Abdul, or the client.

**Results.** At each review every open line gets graduate, keep or stop, and keep has no limit. The page shows each line's age and the audit's Speed row measures it, so an old MVP stays in view without a rule that forces it out. This drops the one-keep limit from "What moves an MVP to the careful lane", and with it the "waiting for the careful lane" exception. The cost: an MVP Abdul forgets to stop stays live until a review where he stops it, with its age on every page until then.

A client's site needs no rule of its own. The client is the named person who will put real data in within a week, so the site graduates at delivery.

**Limits.** The one-day, three-day and one-page limits go. Nothing checked them, so they were reminders, and the kit site broke two of them. The prototype holds all of the look and behaviour, and Abdul spends as long on it as the product needs. The build session adds only what fake data cannot do: email, real content, storage and the deploy. It does not design again.

The brief keeps its six parts with no length limit, and its template sends the decisions made in the prototype review to `prototype/decisions.md`. Measured on the kit site: of 1,748 words, 872 are the prototype section, mostly review rulings, and 9 of the 12 done checks are standard for any site. A 500-word limit had no measured basis (it was one printed page), and it would still refuse the kit site's brief at about 800 words once those two parts move out.

**Standard checks by type.** A `site` runs the shared `site-checks` skill in the plugin: Lighthouse scores, JavaScript size, broken links, titles and meta text, JSON-LD, the sitemap with `llms.txt` and `robots.txt`, the honeypot and rate limit, no sideways scroll, and axe. Its numbers are defaults that a brief can change in one line. The brief lists only the checks particular to its product; for the kit site, the main flow, the real send with the PNG, and the 253 products. An `app` gets no set for now, and the type decides nothing else. The stage-one build session writes `site-checks`, starting from the kit site's brief.

**Done.** The session that deploys writes the live date. The build agent makes the side-by-side page with the browser tool it already uses, at the prototype's viewports: screenshots in pairs, in one Markdown file in the MVP's repo. It marks each difference in layout, controls and flow, never in data, labels each one intended (with the reason) or unintended, and marks each screen the prototype did not have as "new". The person the line is for approves the page and accepts done. Abdul says so in any session or at the next review, and the review writes the done date. The Speed row reads the live date, so a late done date skews nothing.

**The kit site.** It waits for version 2 instead of building on version 1. Abdul judged that finishing it properly on version 1 would take longer than building stage one, and that a version 1 build would drift from what version 2 would build. The order: this ticket, then the fast-lane half of "How a change goes live", then the stage-one build session, then the kit site's build session on version 2, from the prototype approved on 1 November. At delivery the site graduates: the pre-launch gate in `coderules` runs and passes, then the client's inbox and domain go in. Its core design and screenshot baselines are written when stage two lands, alongside Orderflow's and procurement's. The rule in "Whether version 2 is built in two stages" now reads: no MVP graduates before stage two, except one a waiting client needs.

**History out of skill files.** Abdul raised this in the session: asked to update a skill, agents write the when, why and who-ruled into it. Today 16 of the 35 skill files hold dates or "ruled" lines, 154 of them in the four largest. A length limit cannot refuse this, since it passes a short file full of history and refuses a long file of good rules. So the push check refuses a `SKILL.md` or agent file that contains a date (`2026-11-01` or "1 November 2026"), "ruled" or "changed by". A ruling goes to `~/.claude/rulings.md`, a reason to the commit message, a decision to its map ticket. `writing-for-agents` gains one sentence: a skill states the current rule in the present tense, and history goes in the commit message or `rulings.md`. The line limit on skill files stays as "How a regular audit keeps the workflow small" set it, measured at the switch, once version 1's largest files have retired and the history check has stripped the rest.

**Turned down.** A separate category for client work: two sets of rules where the graduation test already covers a client. A hook that stops a session at a day limit: it breaks an auto-mode `/goal` run, and the page shows the overrun anyway. A 500-word brief limit: no measured basis, and it refuses useful detail. A pixel diff for the side-by-side page: fake data against test data marks every screen, as Orderflow's 2,175 difference rows showed. A 1,000-word limit on skill files today: it would measure files that retire at the switch.

`CONTEXT.md` now defines the MVP list and drops "one page" from the brief.

Changed by "How a product graduates, stops or switches over" (2026-11-01): procurement's core design is not written when stage two lands. It waits for the revamp, as "What happens to procurement and the other chain work" decided; only Orderflow's and the kit site's are written then.
