# Manifest — where each published file comes from

This repo holds curated public copies. The live files Claude Code actually reads
stay in `~/.claude/`. When a live file changes and should be published, a session
syncs it here deliberately (never automatically), re-running the scrub rules below.

| Published | Live source |
|-----------|-------------|
| `skills/run-issues/SKILL.md` | `~/.claude/skills/run-issues/SKILL.md` |
| `skills/parallel-hunt/SKILL.md` | `~/.claude/skills/parallel-hunt/SKILL.md` |
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
3. Re-read every changed file end to end before pushing. Publishing is a
   decision, not a side effect.
