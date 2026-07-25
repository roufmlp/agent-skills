# Manifest — where each published file comes from

This repo holds curated public copies. The live files Claude Code actually reads
stay in `~/.claude/`. When a live file changes and should be published, a session
syncs it here deliberately (never automatically), re-running the scrub rules below.

| Published | Live source |
|-----------|-------------|
| `skills/run-issues/SKILL.md` | `~/.claude/skills/run-issues/SKILL.md` |
| `skills/run-issues/decisions.md` | `~/.claude/skills/run-issues/decisions.md` |
| `skills/parallel-hunt/SKILL.md` | `~/.claude/skills/parallel-hunt/SKILL.md` |
| `skills/parallel-hunt/decisions.md` | `~/.claude/skills/parallel-hunt/decisions.md` |
| `agents/*.md` | `~/.claude/agents/*.md` (11 role definitions the two orchestration skills spawn) |
| `docs/model-and-effort-choices.md` | written for this repo; no live source |
| `docs/case-study-five-issue-run.md` | written for this repo; no live source |
| `skills/designrules/designrules.md` | `~/.claude/designrules.md` |
| `skills/designrules/SKILL.md` | `~/.claude/skills/designrules/SKILL.md` (pointer adapted for this repo) |
| `skills/memory-reel/` | Claude desktop app personal skill (export from Settings → Skills) |
| `steering/CLAUDE.md` | `~/.claude/CLAUDE.md` |
| `steering/writingrules.md` | `~/.claude/writingrules.md` |
| `steering/coderules.md` | `~/.claude/coderules.md` |

## Scrub rules (run on every sync)

1. Remove personal housekeeping lines (master-copy locations and sync notes
   pointing into my private notes vault).
2. Remove project-specific paths and client-identifying names. Tools and
   platforms (Zoho, Vercel, Supabase) may stay; client and product names may not.
3. **The published pack runs unchanged, on any repo, with nothing outside it.**
   Instructions name a role ("the human"), never me. Anything the live copy
   assumes because my setup provides it — a project-local skill, a specific model,
   a named memory file, a standing decision recorded in a repo's CLAUDE.md —
   becomes a conditional ("if the project has one") or goes. The one dependency
   allowed is the agent files in `agents/`, which ship in this repo. The steering
   docs are exempt: they are published as personal taste, under my name, to be
   replaced rather than adopted.
4. Re-read every changed file end to end before pushing. Publishing is a
   decision, not a side effect.
