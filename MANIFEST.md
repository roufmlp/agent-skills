# Manifest — where each published file comes from

This repo holds curated public copies. The live files Claude Code actually reads
stay in `~/.claude/`. When a live file changes and should be published, a session
syncs it here deliberately (never automatically), re-running the scrub rules below.

Listed in the order the loop runs.

| Published | Live source |
|-----------|-------------|
| `skills/harden-issues/SKILL.md` | `~/.claude/skills/harden-issues/SKILL.md` |
| `skills/harden-issues/decisions.md` | `~/.claude/skills/harden-issues/decisions.md` |
| `skills/run-issues/SKILL.md` | `~/.claude/skills/run-issues/SKILL.md` |
| `skills/run-issues/decisions.md` | `~/.claude/skills/run-issues/decisions.md` |
| `skills/parallel-hunt/SKILL.md` | `~/.claude/skills/parallel-hunt/SKILL.md` |
| `skills/parallel-hunt/decisions.md` | `~/.claude/skills/parallel-hunt/decisions.md` |
| `skills/daily-brief/SKILL.md` | `~/.claude/skills/daily-brief/SKILL.md` |
| `skills/panel-review/SKILL.md` | `~/.claude/skills/panel-review/SKILL.md` |
| `skills/panel-review/references/deriving-a-panel.md` | `~/.claude/skills/panel-review/references/deriving-a-panel.md` |
| `skills/panel-review/references/running-a-panel.md` | `~/.claude/skills/panel-review/references/running-a-panel.md` |
| `agents/*.md` | `~/.claude/agents/*.md` (15 role definitions the orchestration skills spawn) |
| `docs/model-and-effort-choices.md` | written for this repo; no live source |
| `docs/case-study-five-issue-run.md` | written for this repo; no live source |
| `skills/designrules/SKILL.md` | `~/.claude/skills/designrules/SKILL.md` (pointer adapted for this repo) |
| `steering/CLAUDE.md` | `~/.claude/CLAUDE.md` |
| `steering/writingrules.md` | `~/.claude/writingrules.md` |
| `steering/coderules.md` | `~/.claude/coderules.md` |
| `steering/designrules.md` | `~/.claude/designrules.md` |

Two parts of `~/.claude/CLAUDE.md` never ship:

- The `## Public skills repo` section. It names this repo's location on my machine,
  and rule 1 below covers it.
- The `triage` parenthetical under `## The chain, and where to start`. It publishes
  what my repos do not have. No rule reaches it, so it is named here.

## Scrub rules (run on every sync)

1. Remove personal housekeeping lines: master-copy locations, sync notes, and any
   line naming a path on my machine, including this repo's own location, a notes
   vault, or a project checkout. This governs the files being published. The source
   table above names live paths on purpose, and stays.
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

## What ships, and what does not

The four skills here are one loop: `harden-issues` sharpens the criteria,
`run-issues` builds to them, `parallel-hunt` hunts what per-issue gates cannot see,
`daily-brief` is the single place a human answers what the loop could not decide.
They reference each other, so they ship together or the references dangle.

Two upstream skills are deliberately **not** published: `to-issues` and `to-prd`.
My copies are modified forks of Matt Pocock's skills, and republishing a fork is an
attribution question rather than a scrub question. Where the pack refers to work
arriving from upstream, it names the shape of the input — an issue file with
`Status:`, acceptance criteria and `## Must still be true` — never a skill you
cannot get. `triage` is unpublished for the same reason.
