# Manifest — where each published file comes from

This repo holds curated public copies. The live files Claude Code actually reads
stay in `~/.claude/`. When a live file changes and should be published, a session
syncs it here deliberately (never automatically), re-running the scrub rules below.

Listed in the order the loop runs.

| Published | Live source |
|-----------|-------------|
| `skills/harden-issues/SKILL.md` | `~/.claude/skills/harden-issues/SKILL.md` |
| `skills/harden-issues/decisions.md` | `~/.claude/skills/harden-issues/decisions.md` |
| `skills/harden-issues/test_skill_structure.py` | `~/.claude/skills/harden-issues/test_skill_structure.py` (refuses a slim that carries a rule out with its story) |
| `skills/run-issues/SKILL.md` | `~/.claude/skills/run-issues/SKILL.md` |
| `skills/run-issues/decisions.md` | `~/.claude/skills/run-issues/decisions.md` |
| `skills/run-issues/finale.md` | `~/.claude/skills/run-issues/finale.md` |
| `skills/run-issues/resume.md` | `~/.claude/skills/run-issues/resume.md` |
| `skills/run-issues/launch-harden.md` | `~/.claude/skills/run-issues/launch-harden.md` (the hardening phase a run reads at launch when a named issue in its scope carries no `Hardened:` stamp; off the common path, like `finale.md` and `resume.md`) |
| `skills/run-issues/check_attempt_cap.py` | `~/.claude/skills/run-issues/check_attempt_cap.py` |
| `skills/run-issues/check_finale_stage.py` | `~/.claude/skills/run-issues/check_finale_stage.py` |
| `skills/run-issues/check_diff_coverage.py` | `~/.claude/skills/run-issues/check_diff_coverage.py` |
| `skills/run-issues/find_live_ledger.py` | `~/.claude/skills/run-issues/find_live_ledger.py` |
| `skills/run-issues/orchestrator_cost.py` | `~/.claude/skills/run-issues/orchestrator_cost.py` |
| `skills/run-issues/check_commit_order.py` | `~/.claude/skills/run-issues/check_commit_order.py` |
| `skills/run-issues/check_harden_branch.py` | `~/.claude/skills/run-issues/check_harden_branch.py` |
| `skills/run-issues/check_issue_ready.py` | `~/.claude/skills/run-issues/check_issue_ready.py` |
| `skills/run-issues/check_paste_file.py` | `~/.claude/skills/run-issues/check_paste_file.py` |
| `skills/run-issues/check_permission_floor.py` | `~/.claude/skills/run-issues/check_permission_floor.py` |
| `skills/run-issues/check_run_picture.py` | `~/.claude/skills/run-issues/check_run_picture.py` |
| `skills/run-issues/check_origin.py` | `~/.claude/skills/run-issues/check_origin.py` (refuses a register row or a minted issue that does not name the issue and run that shipped the code) |
| `skills/run-issues/empty_input.py` | `~/.claude/skills/run-issues/empty_input.py` (one refusal for a reader handed nothing, so an empty input never reads as a clean result) |
| `skills/run-issues/check_register_status.py` | `~/.claude/skills/run-issues/check_register_status.py` (refuses a register row whose status cell cannot be read) |
| `skills/run-issues/model_map.py` | `~/.claude/skills/run-issues/model_map.py` (resolves a launch line's model map to one model per role) |
| `skills/run-issues/model-map.default` | `~/.claude/skills/run-issues/model-map.default` (the map a launch that names none falls back to) |
| `skills/run-issues/run_session.py` | `~/.claude/skills/run-issues/run_session.py` (the one road from a batch id to that run's transcript) |
| `skills/run-issues/run_quality.py` | `~/.claude/skills/run-issues/run_quality.py` (reads a run's own ledger and journal into the finale's trial table) |
| `skills/run-issues/cache_probe.py` | `~/.claude/skills/run-issues/cache_probe.py` |
| `skills/run-issues/estimate_accuracy.py` | `~/.claude/skills/run-issues/estimate_accuracy.py` |
| `skills/run-issues/harness_cost.py` | `~/.claude/skills/run-issues/harness_cost.py` |
| `skills/run-issues/run_costs.py` | `~/.claude/skills/run-issues/run_costs.py` |
| `skills/run-issues/run_records.py` | `~/.claude/skills/run-issues/run_records.py` (owns `runs.jsonl`, `issues.jsonl` and the page generated from them) |
| `skills/run-issues/run_measures.py` | `~/.claude/skills/run-issues/run_measures.py` (one line per issue: the estimate, the spans, the verdicts and the five kind facts) |
| `skills/run-issues/run_step.py` | `~/.claude/skills/run-issues/run_step.py` (stamps the finale's named mechanical steps, which a transcript cannot time) |
| `skills/run-issues/pipeline_fingerprint.py` | `~/.claude/skills/run-issues/pipeline_fingerprint.py` (the three repository heads a run launched on, with a dirty mark each) |
| `skills/run-issues/run_compare.py` | `~/.claude/skills/run-issues/run_compare.py` (reads the records across runs; the fact behind `/run-compare`) |
| `skills/run-issues/run_replay.py` | `~/.claude/skills/run-issues/run_replay.py` (the one-time backfill of seven lines written before the fields existed) |
| `skills/run-issues/migrate_view.py` | `~/.claude/skills/run-issues/migrate_view.py` (carried the markdown table into the records, once) |
| `skills/run-issues/run_timings.py` | `~/.claude/skills/run-issues/run_timings.py` |
| `skills/run-issues/check_run_rail.py` | `~/.claude/skills/run-issues/check_run_rail.py` (refuses a rail block a renderer could not transcribe) |
| `skills/run-issues/draw_run_rail.py` | `~/.claude/skills/run-issues/draw_run_rail.py` (draws the rail as SVG from that block; the only road to it) |
| `skills/run-compare/SKILL.md` | `~/.claude/skills/run-compare/SKILL.md` (answers whether the pipeline is getting cheaper, faster or better; reads, never writes) |
| `skills/run-compare/test_skill_structure.py` | `~/.claude/skills/run-compare/test_skill_structure.py` (refuses a skill that grows a writing road, a threshold or a spawn) |
| `skills/run-issues/test_*.py` | `~/.claude/skills/run-issues/test_*.py` (32 files, 1,379 cases, grading the skill text and its scripts; 28 of them skip themselves where a corpus of real ledgers is absent, which is every machine but the author's) |
| `skills/parallel-hunt/SKILL.md` | `~/.claude/skills/parallel-hunt/SKILL.md` |
| `skills/parallel-hunt/decisions.md` | `~/.claude/skills/parallel-hunt/decisions.md` |
| `skills/parallel-hunt/glossary.md` | `~/.claude/skills/parallel-hunt/glossary.md` |
| `skills/parallel-hunt/test_hunt_cost_step.py` | `~/.claude/skills/parallel-hunt/test_hunt_cost_step.py` |
| `skills/daily-brief/SKILL.md` | `~/.claude/skills/daily-brief/SKILL.md` |
| `skills/daily-brief/test_skill_structure.py` | `~/.claude/skills/daily-brief/test_skill_structure.py` (refuses the return of the deleted "row above" rule) |
| `skills/daily-brief/move_closed_sections.py` | `~/.claude/skills/daily-brief/move_closed_sections.py` |
| `skills/daily-brief/test_move_closed_sections.py` | `~/.claude/skills/daily-brief/test_move_closed_sections.py` |
| `skills/lib/check_verdict.py` | `~/.claude/skills/lib/check_verdict.py` (shared by the four skills that spawn adversarial agents) |
| `skills/lib/test_check_verdict.py` | `~/.claude/skills/lib/test_check_verdict.py` |
| `skills/lib/check_decision_ledger.py` | `~/.claude/skills/lib/check_decision_ledger.py` (refuses a decision walk that ends without a costed ledger) |
| `skills/lib/test_check_decision_ledger.py` | `~/.claude/skills/lib/test_check_decision_ledger.py` |
| `skills/lib/claim_number.py` | `~/.claude/skills/lib/claim_number.py` (claims an issue or migration number atomically across every worktree) |
| `skills/lib/test_claim_number.py` | `~/.claude/skills/lib/test_claim_number.py` |
| `skills/lib/collect_shards.py` | `~/.claude/skills/lib/collect_shards.py` (generates `register.md` and `decisions-queue.md` from one shard per writer) |
| `skills/lib/test_collect_shards.py` | `~/.claude/skills/lib/test_collect_shards.py` |
| `skills/lib/retired_phrases.py` | `~/.claude/skills/lib/retired_phrases.py` (the retired-wording denylist; one home, shared by the test and the hook) |
| `skills/lib/test_retired_phrases.py` | `~/.claude/skills/lib/test_retired_phrases.py` (reports a superseded sentence that reached a steering file) |
| `skills/lib/run_python_suites.py` | `~/.claude/skills/lib/run_python_suites.py` (runs every `test_*.py` under `~/.claude/skills` and `~/.claude/hooks` from its own directory, and refuses a suite that executed fewer checks than it defines) |
| `skills/lib/test_run_python_suites.py` | `~/.claude/skills/lib/test_run_python_suites.py` (54 cases; the fixture trees are built in `tmp`, so it carries no corpus and skips nothing) |
| `skills/panel-review/SKILL.md` | `~/.claude/skills/panel-review/SKILL.md` |
| `skills/panel-review/references/deriving-a-panel.md` | `~/.claude/skills/panel-review/references/deriving-a-panel.md` |
| `skills/panel-review/references/running-a-panel.md` | `~/.claude/skills/panel-review/references/running-a-panel.md` |
| `agents/*.md` | `~/.claude/agents/*.md` (16 role definitions the orchestration skills spawn) |
| `check_manifest_coverage.py` | written for this repo; no live source |
| `test_check_manifest_coverage.py` | written for this repo; no live source |
| `check_skill_drift.py` | written for this repo; no live source |
| `test_check_skill_drift.py` | written for this repo; no live source |
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

One more class never ships: session records inside the live skill directories —
panel-review transcripts, workflow-redesign notes, `__pycache__`. A skill directory
publishes its instruction files, its scripts and its tests, nothing it accumulated.

Those records are listed here, not just described, because `check_manifest_coverage.py`
refuses every live file that no row and no line below names. Withholding a file is a
decision like publishing one; this is where it gets written down:

**Two test files are withheld, and the reason is the scrub rather than the tests.**
`run-issues/test_run_isolation.py` and `parallel-hunt/test_hunt_isolation.py` grade
that the skill text carries four `node --env-file=<canonical env> scripts/*.mjs`
commands by name — a seed, a sign-in link, a lock wrapper and a teardown. Those
scripts belong to one project and this pack ships no `scripts/` directory, so rule 3
turns the commands into a shape the reader's project fills. A test that pins the
literal commands then grades a machine nobody else has. The rule they exist for
survives in the published prose; the pinning does not travel.

```withheld
~/.claude/skills/run-issues/test_run_isolation.py
~/.claude/skills/parallel-hunt/test_hunt_isolation.py
~/.claude/skills/run-issues/panel-review-*.md
~/.claude/skills/run-issues/workflow-redesign-*.md
~/.claude/skills/run-issues/harness/*
~/.claude/skills/run-issues/harness/fixture/*
~/.claude/skills/run-issues/harness/fixture/src/*
~/.claude/skills/run-issues/harness/fixture/test/*
```

**The run harness is withheld, and this is the decision rather than an oversight.**
`~/.claude/skills/run-issues/harness/` is a fixture project plus a driver that runs a
real `/run-issues` batch against it, so a workflow change can be measured before and
after. Nothing published here invokes it, so withholding it dangles no reference.

Three reasons it waits for a sync that publishes it deliberately:

- **It spends the reader's money by running.** One reading took 62.7 minutes and 4.8M
  weighted tokens. A script in a skill pack that costs that much to invoke needs its
  price on the label, and writing that label is authoring, not scrubbing.
- **`baseline.md` is one machine's readings** — a Claude Code version, a fingerprint,
  a wall clock. That is the same class of one-machine state the hooks below are
  withheld for.
- **`fixture/.claude/settings.json` carries absolute paths from the author's home**,
  which rule H1 would not let a hook ship and which no reader's machine resolves.

Publishing it is a good idea and a later sync should do it, with the fixture's paths
computed and the cost stated at the top of its README.

It takes four withheld lines rather than one because the checker matches with
`PurePath.match`, where `*` does not cross a directory separator. That is the
point of it: a new directory under `harness/` is unlisted again and has to be
decided, rather than being swallowed by a pattern written today.

## The hooks

A hook is not a skill, and this class exists because the difference decides what may
ship. A skill is read by a model that can notice a wrong line and work around it. A
hook is executed by the harness, and it refuses: a wrong path inside one does not get
worked around, it blocks a stranger's edit with a message about a machine that is not
theirs. So the rows below are held to `### Scrub rules for a hook`, which is stricter
than the four that govern everything else here.

| Published | Live source |
|-----------|-------------|
| `hooks/run-issues-foreground-gate.py` | `~/.claude/hooks/run-issues-foreground-gate.py` |
| `hooks/test_run_issues_foreground_gate.py` | `~/.claude/hooks/test_run_issues_foreground_gate.py` (27 behavioural cases, mutation-tested, added 2026-09-07) |
| `hooks/run-issues-evidence-gate.py` | `~/.claude/hooks/run-issues-evidence-gate.py` |
| `hooks/test_run_issues_evidence_gate.py` | `~/.claude/hooks/test_run_issues_evidence_gate.py` |
| `hooks/coderules-gate.py` | `~/.claude/hooks/coderules-gate.py` |
| `hooks/origin-row-guard.py` | `~/.claude/hooks/origin-row-guard.py` (refuses a register table typed without an `origin` column, at the keystroke) |
| `hooks/test_origin_row_guard.py` | `~/.claude/hooks/test_origin_row_guard.py` |
| `hooks/retired-phrases-gate.py` | `~/.claude/hooks/retired-phrases-gate.py` (refuses a write that puts retired wording into a steering file) |
| `hooks/test_retired_phrases_gate.py` | `~/.claude/hooks/test_retired_phrases_gate.py` |
| `hooks/git-shared-state-guard.py` | `~/.claude/hooks/git-shared-state-guard.py` (refuses the git commands that reach across sessions sharing one checkout) |
| `hooks/test_git_shared_state_guard.py` | `~/.claude/hooks/test_git_shared_state_guard.py` (68 behavioural cases against a real git fixture, mutation-tested, added 2026-09-08) |
| `hooks/README.md` | written for this repo; no live source (the install note) |

**`git-shared-state-guard.py` is here on a ruling, and it cost the sync three scrubs.**
Ticket 41 of the pilot-delivery map settled it on 2026-09-07: the fault the guard closes is
a property of git, not of one machine. A worktree gets its own index; the main checkout has
one, and every session working there shares it, so a wide `git add` stages whatever every
other session has touched. Anyone running several agents against one checkout has this.

Copied on 2026-09-08, three things moved. The refusal's closing line cited the ticket and
the dates it was measured on, which H2 forbids; it now states the fact that line carried —
naming what you stage does not protect it while the index is shared — and the test pins that
sentence instead of the ticket number. The docstring gained a blast-radius paragraph at the
top under H4, and its two instances lost a run id, a commit sha and two ticket numbers,
keeping the measured 1,472 lines. And it claimed to copy the shape of
`generated-file-guard.py` "in this same directory", which is withheld: under H3 it now names
the published hooks beside it.

**A hook does nothing until a reader registers it, and a skill pack cannot register it
for them.** That is the whole reason `hooks/README.md` exists: it carries the exact
`settings.json` block, names the event each hook registers on, and says what a reader
who copies the file and skips the block still loses. Publish no hook without a line in
it.

**One of the six published hooks ships no test, `coderules-gate.py`, because it has none
anywhere in the live tree.** Re-measured 2026-09-07 by the session verifying ticket 36, and
still true on 2026-09-08. `run-issues-foreground-gate.py` gained
`test_run_issues_foreground_gate.py` in ticket 36 sitting 1, 27 cases that drive payloads
through it, and that test went out in the 2026-09-08 sync with one paragraph rewritten under
H3: it had listed five sibling test files as evidence of the gap it closed, and four of the
five are withheld from this pack. `coderules-gate.py` is named by no test file at all. That
is a gap in the live tree, not a scrub decision, and it is written here rather than left for
a reader to discover by grepping.

**`origin-row-guard.py` ships with one road switched off, and the reason is a withheld
file rather than a scrub of its own.** Its Bash branch resolves a redirect target with
`generated-file-guard.py`'s `bash_targets` parser, and that file is withheld below. The
published guard therefore passes every Bash write, judges Edit and Write in full, says so
in its own docstring and in `hooks/README.md`, and its two Bash test classes skip
themselves when the parser is absent rather than failing — five skips is the pass here.
Publishing `generated-file-guard.py` would switch the road on with no change to either
file, and that is a decision for a later sync, not a scrub.

**Six hooks arrived in the 2026-09-06 sync and none of them shipped. They are held
back on the rule that already withheld the two below, not on a new judgement.** Three
name a person inside the REFUSAL MESSAGE itself: the `AFK` constant in
`gate-source-write-guard.py` and in `model-map-gate.py`, and the board paragraph in
`run-state-path-guard.py`. Two of them read "THIS NEVER WAITS FOR <name>". H2
refuses that outright, and rewriting a refusal message to a role is authoring rather
than scrubbing. `run-state-path-guard.py` also redirects to one machine's folder. The
other three — `generated-file-guard.py`, `model-landed-check.py`,
`number-claim-guard.py` — are closer, and their tests are what stops them: each reads a
real project checkout or a `.scratch/` layout by name, so it would fail for every
reader, and a hook whose test cannot run is worse evidence than no test.

All six are worth publishing and a later sync should do it, message by message. The
skills that rely on them say so in prose instead: `run-issues/SKILL.md` names the model
map as a rule the runner holds, and says plainly that this pack ships no refusal for it.

**`run-issues-sweep-gate.py` arrived on 2026-09-07 and is withheld on the same rule, with its
test beside it.** Its refusal message carries the `AFK` constant, "THIS NEVER WAITS FOR
<name>", the exact shape H2 refuses in `gate-source-write-guard.py` and `model-map-gate.py`
above. It also imports `check_register_status.py` from the skills tree by a computed path,
which is fine under H1, so the message is the only bar. A later sync that rewrites the
three messages to a role publishes all three together.

**Two of the withheld hooks are held back for a different reason, and it is not
one-machine state.** `run-issues-criteria-fault.py` and `run-issues-parallel-gates.py`
are sound hooks with the blast radius H4 asks for, and a later sync should publish
them. They are not ready today on two counts. Their refusal messages name a person,
which H2 refuses outright — that message is the only part of a hook most readers ever
see, and rewriting it to a role is authoring rather than scrubbing. And their tests
read a real project checkout by absolute path, so they cannot ship under H1 and would
fail for every reader; a hook whose test cannot run is worse evidence than no test.

The rest of the live hooks directory stays unpublished for the original reason. Each
of those files carries state that is true of one machine or one repo and false
everywhere else — a disk and
swap threshold, a CLI version pin, a worktree layout, a per-day browser budget. A
stranger who installed them would be refused by a description of a machine they do not
have, which is worse than having no hook:

```withheld
~/.claude/hooks/gate-source-write-guard.py
~/.claude/hooks/test_gate_source_write_guard.py
~/.claude/hooks/generated-file-guard.py
~/.claude/hooks/test_generated_file_guard.py
~/.claude/hooks/model-landed-check.py
~/.claude/hooks/test_model_landed_check.py
~/.claude/hooks/model-map-gate.py
~/.claude/hooks/test_model_map_gate.py
~/.claude/hooks/number-claim-guard.py
~/.claude/hooks/test_number_claim_guard.py
~/.claude/hooks/run-state-path-guard.py
~/.claude/hooks/test_run_state_path_guard.py
~/.claude/hooks/run-issues-criteria-fault.py
~/.claude/hooks/test_run_issues_criteria_fault.py
~/.claude/hooks/run-issues-parallel-gates.py
~/.claude/hooks/test_run_issues_parallel_gates.py
~/.claude/hooks/run-issues-sweep-gate.py
~/.claude/hooks/test_run_issues_sweep_gate.py
~/.claude/hooks/machine-preflight.py
~/.claude/hooks/test_machine_preflight.py
~/.claude/hooks/heavy-run-version.pin
~/.claude/hooks/browser-budget.py
~/.claude/hooks/worktree-snapshot-notice.py
~/.claude/hooks/test_worktree_snapshot_notice.py
~/.claude/hooks/test_settings_env.py
~/.claude/hooks/TOOL-SET-PROBE.md
```

## The coverage check

```
python3 check_manifest_coverage.py
```

Run it before every sync. It refuses three disagreements between this map and the two
trees: a live file no row names (`unlisted`), a row whose live source has gone
(`dead-source`), and a row whose published file has gone (`dead-publication`).

It reads presence only, never content. The two copies differ by design — the scrub
rules rewrite names, paths and run ids on every sync — so a content check would alarm
on every file for ever and be switched off within a day.

**No row reads `dead-publication` today.** The 2026-09-08 sync copied the six that did:
`skills/run-issues/launch-harden.md`, `skills/lib/run_python_suites.py` and its drill,
`hooks/test_run_issues_foreground_gate.py`, and `hooks/git-shared-state-guard.py` with its
test. Four of them had waited since 2026-09-07, which was the state this paragraph recorded:
a row with no file is the honest state, because the decision to publish is recorded before
the copy is made.

Two of the six needed a rewrite rather than a copy, both under rule 3.
`run_python_suites.py` cited `hooks/model-landed-check.py` in its docstring as a second
instance of the shape it refuses; that hook is withheld, so the sentence now states the
shape without naming a file no reader has. `launch-harden.md` named `model-map-gate.py` and
`machine-preflight.py` as controls its reader holds, and both are withheld: the model-map
line now says in as many words that this pack ships no refusal for it, matching what
`run-issues/SKILL.md` already says, and the two overlap-guard lines became conditionals on
the reader's own setup.

It exists because the reminder it replaces had a hole the shape of the fault. That
reminder fires "after editing any file listed in its MANIFEST.md", and a brand-new live
file is listed nowhere, so it never fired: `check_finale_stage.py` and
`orchestrator_cost.py` were both written live on 2026-08-21 and were still unpublished
on 2026-08-22, when a panel review found them by hand.

## Measuring what changed since the last sync

The coverage check finds new files. It says nothing about a rule that changed inside a
file that already has a row, so content drift needs its own instrument.

**Never diff the two trees against each other to find it.** They differ by design, and
the differences are mostly the scrub doing its job. Diffing them on 2026-08-22 raised 47
differences; 44 were the scrub and 3 were real. Reading 47 judgements to find 3 facts is
what this avoids.

The live skills directory is a git repository. Each sync tags it at the commit it
published, so the next sync reads the drift straight off that tag:

```
git -C ~/.claude/skills diff synced-<date>.. -- <the directories the table above lists>
```

Whatever that prints is unpublished, in full, with no judgement needed. Nothing else is.

**The sync session moves the tag when it finishes, and that is what keeps this true.**
In order: commit the live work, publish here, then tag the live commit with today's date
and name the public commits in the tag message. A sync that skips the tag leaves the
next one with no cheap measurement, and the 47-lead sweep is what it falls back to.

The convention began at `synced-2026-08-22`. Read `git -C ~/.claude/skills tag -n99 -l
"synced-*"` for the sync history and what each one published.

**THREE checkouts hold the published files, and one tag reaches only one of them.**
`~/.claude/skills`, `~/.claude/agents` and `~/.claude` are three separate git
repositories. A sync tags every checkout it published from, and reads each one's drift
off its own tag:

```
git -C ~/.claude/skills diff synced-<date>.. -- <the skill directories above>
git -C ~/.claude/agents diff synced-<date>..              # the agents/*.md row
git -C ~/.claude        diff synced-<date>.. -- hooks/
```

Written down because the skills tag looks like it covers everything under `~/.claude`
and does not. A file edited after a sync that tagged only `~/.claude/skills` is invisible
to every measurement on this page except the coverage check, which sees new files only.

**This is not hypothetical, and the agents row is what proved it.** The 2026-08-31 sync
measured drift off the skills tag alone, found none in `agents/`, and published nothing
there. The agent briefs had last been published on 2026-08-18, and five live commits had
landed since: 363 changed lines across twelve briefs, including the whole of the finale's
citation duty. It went out on 2026-09-01 in a second pass, and the reason it was missed
is the paragraph above, which named the hooks and forgot the agents.

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

### Scrub rules for a hook

These are additional to rules 1-4, and where they disagree with them, these win. A hook
earns stricter rules because of what it is: executed rather than read, and read by a
human only at the moment it has just blocked their work. A skill with a stale line
costs a reader a raised eyebrow. A hook with a stale line costs them a refusal they
cannot act on.

- **H1. No absolute path survives, in code or in prose.** `~/.claude/…` stays: that is
  the reader's own tool directory and resolves on their machine as it does on mine.
  Anything under `/Users/`, `/home/`, or a named project checkout goes. Where the hook
  genuinely needs a real path, it computes one (`os.path.expanduser`) or reads it from
  the environment with a documented default — it never carries mine as a literal.
- **H2. The refusal message names no repo, run id, issue number or person.** That
  message is the only part of a hook most readers will ever see, and it arrives at the
  moment their work is blocked. A message citing a run or a repository they do not have
  reads as a broken install, and a reader who concludes the hook is broken removes it.
- **H3. Every claim in the docstring is true of the PUBLISHED file.** A drill that names
  fixtures the file does not carry, or a companion document this pack does not ship, is
  rewritten to what the published copy can actually do, or cut. Recorded because
  `run-issues-foreground-gate.py` carried both on 2026-08-23: a drill naming payloads in
  a `__main__` block that holds none, and `docs/patterns.md` in a repo no reader has.
- **H4. The docstring states the blast radius before anything else**: the event it
  registers on, what it matches, what it refuses, and what it deliberately lets past. A
  hook that cannot say what it will *not* block does not ship, because a reader cannot
  consent to a control whose reach is unstated.
- **H5. It fails open on input it cannot read.** Every published hook returns 0 on a
  payload that will not parse. A hook that raises takes the reader's tool call with it,
  and a stack trace at a `PreToolUse` boundary is a fault this pack introduced into
  somebody else's session.
- **H6. It writes nothing outside a temporary directory, and nothing that outlives the
  machine's next restart.** A published hook that creates or edits a file in a reader's
  repository is doing more than refusing.
- **H7. Rule 4, twice.** Read the published copy end to end, then run it: feed it a
  payload that must pass and one that must be refused, and check both exit codes. A hook
  is the one class here where reading the diff is not enough, because the harness will
  execute it verbatim.

## What ships, and what does not

The four skills here are one loop: `harden-issues` sharpens the criteria,
`run-issues` builds to them, `parallel-hunt` hunts what per-issue gates cannot see,
`daily-brief` is the single place a human answers what the loop could not decide.
They reference each other, so they ship together or the references dangle.

The scripts ship for the same reason. A 2026-08 audit of the loop replaced its
weakest reminders with refusals — small Python checks the skills now invoke — and a
`SKILL.md` that calls a script it does not ship breaks rule 3. So the scripts and
the tests beside them are part of the pack, and every one of them gets the same
scrub as the prose.

Two upstream skills are deliberately **not** published: `to-issues` and `to-prd`.
My copies are modified forks of Matt Pocock's skills, and republishing a fork is an
attribution question rather than a scrub question. Where the pack refers to work
arriving from upstream, it names the shape of the input — an issue file with
`Status:`, acceptance criteria and `## Must still be true` — never a skill you
cannot get. `triage` is unpublished for the same reason.
