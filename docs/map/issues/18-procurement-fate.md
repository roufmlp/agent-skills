Status: resolved
Assignee: Abdul (wayfinder session 2026-10-31)
Type: grilling
Blocked by: 12

# What happens to procurement and the other chain work

## Question

"What happens to Orderflow" settled the pattern for a live product the chain built: version 1 holds until the switch, then a brief, a sweep that turns the risk-class items still true into draft change notes, and `.scratch/` left at a `v1` tag. Procurement (TenderFlow) is the other big repo on the chain, and it may need a different answer. It is unclear whether it is an MVP or a product. The client's founder has worked in its pilot project every day since 20 August (36 problem reports, 5 purchase orders and 63 supplier contacts by 28 August), yet no document has reached a real customer or supplier, and the plan of record mints a fresh live database and domain at real launch. By the glossary, the founder's data may already count as real. It also has 190 issue files of waiting work, 151 of them not yet hardened, while no run is live and its last commit on main was on 23 October. Decide which lane procurement is in, whether it graduates and when, and whether its waiting work finishes on the chain, becomes change notes or stays at the tag. Two smaller repos hold unfinished issue files too: arabic-home has 17 and family-meals has 5, and neither has had a commit since late September. Decide whether each is an MVP, a product or a stop.

## Answer

Procurement is a product and joins the careful lane at the switch, parked until the brainstorm session picks its revamp. arabic-home and family-meals are family tools, not apps, so neither lane applies to them.

**Procurement is real.** The pilot holds the 149 suppliers and about 80 buyers imported from the client's own Zoho books, and the founder worked in it daily from 20 August. Mail went only to Abdul's own test addresses and no document reached a real firm, but a customer's business data counts as real from the first day. Abdul also wants no risk taken on an app that handles money, sign-in, AI and several other integrations. Nobody uses it today, and it needs a revamp.

**Parked, then revamped in the careful lane.** It does nothing until the brainstorm session picks the revamp, which goes into the idea log like any other idea. Retiring it and starting again as an MVP was rejected: the revamp keeps the idea, so the code and the data are worth keeping.

**The waiting work stays at the `v1` tag.** The ticket's 190 was wrong. On 31 October `.scratch/tenderflow-pilot/issues/` held 642 issue files, 455 done and 157 open, about 150 of them not hardened. The open files, the 189 sections of the decisions queue and the run records all stay readable at the tag. When the revamp starts, the session that writes the core design reads the 40 or so open files that touch a risk class and turns those that still apply into change notes. A sweep at the switch, as Orderflow gets, was rejected: nobody uses procurement, and the revamp may replace the code a sweep would check.

**The switch does three things.** It commits the two modified files left in the working tree, tags `v1` and removes `.scratch/` from main, and adds the careful-lane block to procurement's `CLAUDE.md`. The brief, the core design and the pre-launch gate wait for the revamp, which would rewrite the first two anyway. The gate runs before the revamp's first push.

**The app goes offline now.** On 31 October the lockfile on main pinned Next.js 16.2.10, against which npm lists 21 advisories, six of them critical remote code execution. Most need a feature in use, such as SVG or AVIF images, and nobody has checked which ones procurement uses. An app with real data and no users gains nothing from staying live, so the Vercel project and its four crons are paused as a version 1 action, before the switch. The database stays. Pausing takes one CLI command, and so does resuming; Abdul runs it, because the command asks him to type the project name. He paused it on 31 October, and the site and its four cron paths now answer 503 `DEPLOYMENT_PAUSED`. One cron renews the mail subscriptions, so they lapse while the app is paused, and the revamp sets them up again. Upgrading Next.js and staying live was rejected because it needs a test and a push for an app nobody watches. Two smaller items from procurement's pending file are softer than they looked: the Function Storage alert of 11 October counts a rolling 30 days and may have dropped since, and the QA password reached only one local transcript on this laptop, so rotating it is optional.

**The risk classes stay at five.** Abdul named AI and third-party integrations as risky. Every integration carries a key, so "secrets" covers it, and a sixth class would add a rule to every MVP. If the audit finds integration bugs the five classes missed, the class comes then.

**arabic-home and family-meals get no lane.** arabic-home is a plan for speaking Arabic at home with printable weekly sheets; its 17 issue files hold one open. family-meals runs as a Friday meal plan; its 15 issue files hold none open. Neither gets a lane line in its `CLAUDE.md`, the switch does no work on them, and they stay out of the brainstorm review.

`CONTEXT.md` now says a customer's pilot data is real from the first day, and defines parked.
