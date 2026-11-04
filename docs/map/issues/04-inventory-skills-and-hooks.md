Status: resolved
Type: research

# What each skill and hook does today

## Question

For each of the 35 skill folders in this repo, and each of the hooks registered in `~/.claude/settings.json`, what does it do, which step of today's chain uses it, and does it hold anything private? Sort each into a draft bucket: likely fast lane, likely careful lane, version 1 record only, or personal and never public. The sort feeds "What the careful lane keeps"; it decides nothing itself.

## Answer

The repo holds 35 skills. `settings.json` registers 33 distinct hook scripts, not 31; one more guard, `run-issues-risk-path-guard.py`, exists but is not registered. Sixteen agent files in `~/.claude/skills/workflow/agents/` belong to the chain skills.

Draft sort, not a decision:

| Bucket | Skills | Hooks |
|---|---|---|
| Fast lane | 15 | 7 |
| Careful lane | 12 | 18 |
| Version 1 record only | 7 | 8 |
| Personal, never public | 1 (writingrules) | 1 (pilot-database-guard) |

Seventeen of the 18 careful-lane hooks exist only to guard run-issues, so if run-issues retires they all go to the version 1 record. None of the 15 fast-lane skills carries private material. Most private material sits in run-issues (142 files), `lib/` (44), harden-issues and daily-brief.

Findings: `.scratch/workflow-v2/research/04-inventory-skills-and-hooks.md` on branch `research/inventory-skills-and-hooks`.
