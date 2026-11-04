Status: resolved
Type: research

# What in this repo is private

## Question

What does this live repo hold that must not go public? Scan the skills, `lib/`, `docs/`, `.scratch/` and the hooks they reference for customer and project names, absolute paths, memory references, rulings evidence and anything else the scrub rules in `~/code/agent-skills/MANIFEST.md` strip today. List each kind, where it lives and how many files carry it. Then measure what scrubbing costs today: how often a sync has run and how much it changed, from the git history of `~/code/agent-skills`.

## Answer

No keys, tokens or phone numbers anywhere in 591 files scanned; the only real email addresses sit in two test fixtures. The private material is names and paths: "orderflow" in 228 files, "procurement" in 80, the home path in 121, Abdul's name in 382, memory-directory references in 35, `pending-on-abdul` in 17, and `rulings.md` cited in 92. About half of it is run history in `.scratch/tracker-tooling` (269 files). Among the skills, run-issues (142 files) and `lib/` (44) carry the most. Twenty skill folders are clean today, wayfinder, grilling and prototype among them.

Scrubbing costs a lot and still leaks. agent-skills has 37 sync commits on 28 days between 19 July and 27 October 2026, one every 2.2 days, averaging 20 files and about 3,000 lines each. Syncs are 94% of every line changed there. The public repo still carries `/Users/` in 7 files, Abdul's name in 3 and `rulings.md` in 20.

Findings: `.scratch/workflow-v2/research/06-private-material-in-the-repo.md` on branch `research/private-material-in-the-repo`.
