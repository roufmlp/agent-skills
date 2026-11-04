Status: done
Type: research result for ticket 06, private material in the repo

# What in this repo is private

Measured on 2026-10-27. I scanned 591 text files: every skill folder, `lib/`, `docs/`, `.scratch/`, `.claude/` and `UPSTREAM.md`. The folder `synced/` does not exist in this repo. The hooks live outside it, in `~/.claude/hooks/`, so I counted them as a separate row. I read no secret value. The numbers are counts of files.

## What counts as private today

The scrub rules in `~/code/agent-skills/MANIFEST.md` strip: paths on Abdul's machine (rule 1); client and product names, while tools such as Zoho and Vercel may stay (rule 2); anything the pack assumes from his setup, such as named memory files and his own name (rule 3); every `/Users/` path in a hook (H1); and any repo, run id, issue number or person in a refusal message (H2).

## Kinds, places and counts

| Kind | Where it lives | Files | Example path |
|---|---|---|---|
| Project name "orderflow" | `.scratch/tracker-tooling` 132, `run-issues` 38, `lib` 29, `skills(other)` 16, `decisions-queue.d` 11, `rulings.md` 1, `floor-transcripts` 1 | 228 | `lib/check_overlap.py` |
| Project name "procurement" | `.scratch/tracker-tooling` 30, `run-issues` 32, `lib` 10, `skills(other)` 6, `decisions-queue.d` 2 | 80 | `.scratch/decisions-queue.d/skill-repo-scrub-sync-651c4c/q-sq44.md` |
| Checkout path `code/procurement` or `code/orderflow` | `.scratch/tracker-tooling` 52, `run-issues` 21, `lib` 3 | 80 | `.scratch/floor-transcripts/PROMPT.md` |
| Absolute home path | `.scratch/tracker-tooling` 84, `run-issues` 22, `lib` 4, `decisions-queue.d` 3, `.claude` 1 | 121 | `.claude/settings.json` |
| Abdul's name or login | `.scratch` 215, `run-issues` 100, `lib` 36, `skills(other)` 30 | 382 | `lib/check_queue_shard.py` |
| Memory-directory reference (`.claude/projects`, `MEMORY.md`, `/memory/`) | `.scratch/tracker-tooling` 21, `run-issues` 5, `lib` 3, `skills(other)` 4 | 35 | `.scratch/floor-transcripts/PROMPT.md` |
| `pending-on-abdul` | `tracker-tooling` 4, `lib` 4, `run-issues` 5, `skills(other)` 4 | 17 | `daily-brief/SKILL.md` |
| Rulings evidence (`rulings.md`, "Ruled 20xx-") | `.scratch/tracker-tooling` 50, `decisions-queue.d` 16, `lib` 8, `run-issues` 7, `skills(other)` 11 | 92 cite `rulings.md`; 17 carry a dated ruling | `.scratch/rulings.md` |
| Real email addresses | test fixtures only | 2 (one company domain, one personal) | `lib/test_class_only_edit.py`, `run-issues/test_run_isolation.py` |
| Customer-site env names (`SUPABASE_`, `RESEND_`, `ZOHO_`) | `run-issues` 15, `tracker-tooling` 4, `skills(other)` 1 | 20 | `run-issues/check_permission_floor.py` |
| Tokens, keys, private keys | none found | 0 | none |
| Phone numbers | none found | 0 | none |
| Hooks outside the repo, `~/.claude/hooks/` (71 files) | project names 32, `/Users/` path 14, Abdul's name 51, memory path 3 | n/a | `~/.claude/hooks/` |

Notes on the table. Platform names (Zoho, WhatsApp, Supabase, Resend, Vercel) appear in 68 files; the rules allow them. I found no customer name other than the two project names and one company email domain. The pilot customer is not named in any file I scanned. The largest block is `.scratch/tracker-tooling`: 269 files, of which 133 name a project and 188 name Abdul. That folder is run history, not skill text.

## Scrub cost, from `~/code/agent-skills`

- The repo has 88 commits, from 2026-07-19 to 2026-10-27 (100 days).
- 37 are sync commits (subject starts "Sync" or "Publish"). They fall on 28 distinct days, between 2026-07-23 and 2026-10-12. That is a sync about every 2.2 days, or 3 a week.
- Each sync changes 20.4 files and 2,971 lines on average (756 files and 109,944 lines in total). The median is 13 files. The largest is 93 files and 18,232 lines, on 2026-09-29.
- The other 51 commits change 8,832 lines in total. Sync commits make up 94% of all changed lines.
- In the last 30 days (since 2026-09-27): 7 sync days, 207 files, 28,385 lines.
- 11 commit subjects name a scrub or a withheld file. The MANIFEST records that a scrub does not stay done: on 2026-09-13 three files came back with scrubs that had been undone. Abdul now diffs each published copy before every re-publish.
- The scrub is not complete. In the public repo, `/Users/` still appears in 7 files (tests and hooks), Abdul's name in 3, and `rulings.md` in 20. No file there names "orderflow", "procurement" or `pending-on-abdul`, except the MANIFEST itself.

## Folders that are clean today

Clean means no project name, no `/Users/` path, no memory reference and no Abdul. Twenty folders:

`ask-matt`, `codebase-design`, `diagnosing-bugs`, `docs`, `domain-modeling`, `grill-me`, `grill-with-docs`, `grilling`, `handoff`, `improve-codebase-architecture`, `prototype`, `research`, `resolving-merge-conflicts`, `setup-matt-pocock-skills`, `teach`, `to-questionnaire`, `wait-what`, `wayfinder`, `wizard`, `writing-for-agents`. So is `.scratch/workflow-audit`.

Nearly clean, with only Abdul's name: `panel-review`, `run-compare`, `tdd`, `triage`, `to-prd`, `UPSTREAM.md`.

Not clean: `run-issues` (142 files), `lib` (44), `.scratch/tracker-tooling` (269), the other `.scratch` folders, `harden-issues`, `daily-brief`, `parallel-hunt`, `premise-check`, `to-issues`, the code, design, question and writing rules, and `.claude`.

Gist: private material sits in run history (`.scratch`), the loop skills with their tests, and the hooks. None of it is a secret. All of it is identity and project detail.
