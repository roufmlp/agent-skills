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
| `skills/harden-issues/check_criteria_edit.py` | `~/.claude/skills/harden-issues/check_criteria_edit.py` (refuses a hardening edit that adds a criterion beside a reset one, writes a count nobody measured, or gives an example input and outcome with no command in its clause; imports the criterion reader from `run-issues/check_issue_ready.py`) |
| `skills/harden-issues/test_check_criteria_edit.py` | `~/.claude/skills/harden-issues/test_check_criteria_edit.py` (41 cases on fixtures built in `tmp`; carries no corpus and skips nothing) |
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
| `skills/run-issues/check_briefing_commands.py` | `~/.claude/skills/run-issues/check_briefing_commands.py` (refuses a merge briefing whose commands carry no run evidence beside them) |
| `skills/run-issues/citation_pass.py` | `~/.claude/skills/run-issues/citation_pass.py` (the one reader of the finale's citation deltas) |
| `skills/run-issues/correction_brief.py` | `~/.claude/skills/run-issues/correction_brief.py` (composes a correction implementer's spawn prompt; loads `hooks/run-issues-brief-cap.py` for the exemption marker) |
| `skills/run-issues/correction_close.py` | `~/.claude/skills/run-issues/correction_close.py` (authorises a correction round's close on named evidence, never on files having been touched) |
| `skills/run-issues/report_brief_cap.py` | `~/.claude/skills/run-issues/report_brief_cap.py` (reads the brief-cap hook's diary into the finale's measure step) |
| `skills/run-issues/report_claim_commands.py` | `~/.claude/skills/run-issues/report_claim_commands.py` (one claim script for the commands a briefing states) |
| `skills/run-issues/stall_watch.py` | `~/.claude/skills/run-issues/stall_watch.py` (watches a run's ledger from its own process, because a cron fires only when the REPL is idle) |
| `skills/run-issues/read_session_settings.py` | `~/.claude/skills/run-issues/read_session_settings.py` (prints the session's model and effort and names the file or flag each was read from) |
| `skills/run-issues/check_run_journal.py` | `~/.claude/skills/run-issues/check_run_journal.py` (refuses a run journal that has fallen behind its own ledger; imports the table parser from `check_commit_order.py`) |
| `skills/run-issues/check_drill_coverage.py` | `~/.claude/skills/run-issues/check_drill_coverage.py` (refuses a gate verdict that grades a drill-carrying criterion on the implementation record's evidence without saying so) |
| `skills/run-issues/seams_from_commits.py` | `~/.claude/skills/run-issues/seams_from_commits.py` (the files more than one issue of a run touched, taken from the commits rather than from what the issue files predicted; the script `agents/run-issues-finale.md` names) |
| `skills/run-issues/criteria_ids.py` | `~/.claude/skills/run-issues/criteria_ids.py` (the one reader of an issue's criterion and invariant names, and of the names a text cites) |
| `skills/run-issues/charge_round.py` | `~/.claude/skills/run-issues/charge_round.py` (decides what one gate round charges from both gates' per-item grades, so a strike lands only on a named criterion; imports `retry_brief.py` and `issue_level.py`) |
| `skills/run-issues/retry_brief.py` | `~/.claude/skills/run-issues/retry_brief.py` (composes a retry implementer's spawn prompt, or refuses to; shipped from 2026-09-29; the `retry_brief.py` paragraphs under this table say why) |
| `skills/run-issues/issue_level.py` | `~/.claude/skills/run-issues/issue_level.py` (reads the level an issue runs at fresh from its file on every call; imports `lib/set_level.py`) |
| `skills/run-issues/check_briefing_blocked.py` | `~/.claude/skills/run-issues/check_briefing_blocked.py` (refuses a merge briefing that leaves out an issue the run blocked) |
| `skills/run-issues/finale_reds.py` | `~/.claude/skills/run-issues/finale_reds.py` (turns the finale suite's red files into register rows, one row per file) |
| `skills/run-issues/make_copy.py` | `~/.claude/skills/run-issues/make_copy.py` (makes a gate's private copy of the run tree, with its history, its uncommitted work and a linked `node_modules`) |
| `skills/run-issues/move_verdicts.py` | `~/.claude/skills/run-issues/move_verdicts.py` (moves gate verdicts out of issue files and into the runs that wrote them; dry run unless `--apply`) |
| `skills/run-issues/run_suite.py` | `~/.claude/skills/run-issues/run_suite.py` (the wrapper every whole-suite reading goes through: logs it, hashes the tree, refuses a repeat) |
| `skills/run-issues/flake_report.py` | `~/.claude/skills/run-issues/flake_report.py` (lists the test files `run_suite.py` has found flaky in one repository, most flakes first, from its flake ledger) |
| `skills/run-issues/wakeup_cron.py` | `~/.claude/skills/run-issues/wakeup_cron.py` (makes the run's 30-minute wakeup cron from its ledger, records the job with the process that made it, clears it, and judges each firing idle or busy) |
| `skills/run-issues/test_wakeup_cron.py` | `~/.claude/skills/run-issues/test_wakeup_cron.py` |
| `skills/run-issues/scoped_suite.py` | `~/.claude/skills/run-issues/scoped_suite.py` (runs every test whose imports reach a changed file, every test that lists a directory, every test whose text names a changed file, and the repo-wide checks, and records it the way `run_suite.py` does) |
| `skills/run-issues/fork_specs.py` | `~/.claude/skills/run-issues/fork_specs.py` (at launch, runs each e2e spec an issue's criteria name at the fork, and refuses the issue when the spec is already red) |
| `skills/run-compare/SKILL.md` | `~/.claude/skills/run-compare/SKILL.md` (answers whether the pipeline is getting cheaper, faster or better; reads, never writes) |
| `skills/run-compare/test_skill_structure.py` | `~/.claude/skills/run-compare/test_skill_structure.py` (refuses a skill that grows a writing road, a threshold or a spawn) |
| `skills/run-issues/test_*.py` | `~/.claude/skills/run-issues/test_*.py` (54 files, 2,406 cases, grading the skill text and its scripts; 8 of them skip cases where a corpus of real ledgers is absent, which is every machine but the author's. Counted 2026-10-11 by running each file) |
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
| `skills/lib/collect_shards.py` | `~/.claude/skills/lib/collect_shards.py` (generates `register.md` and `decisions-queue.md` from one shard per writer, and hides a retired queue item on either of two reserved shards: the brief's `answered` and an attended session's `ruled`; refuses to write the main checkout's board from a linked worktree without `--write-main`, and prints the board with `--print`, writing nothing) |
| `skills/lib/test_collect_shards.py` | `~/.claude/skills/lib/test_collect_shards.py` |
| `skills/lib/retired_phrases.py` | `~/.claude/skills/lib/retired_phrases.py` (the retired-wording denylist; one home, shared by the test and the hook) |
| `skills/lib/test_retired_phrases.py` | `~/.claude/skills/lib/test_retired_phrases.py` (reports a superseded sentence that reached a steering file) |
| `skills/lib/run_python_suites.py` | `~/.claude/skills/lib/run_python_suites.py` (runs every `test_*.py` under `~/.claude/skills` and `~/.claude/hooks` from its own directory, and refuses a suite that executed fewer checks than it defines) |
| `skills/lib/test_run_python_suites.py` | `~/.claude/skills/lib/test_run_python_suites.py` (65 cases; the fixture trees are built in `tmp`, so it carries no corpus and skips nothing) |
| `skills/lib/next_batch.py` | `~/.claude/skills/lib/next_batch.py` (orders the next batch of issues so every blocker lands first, and refuses an order it cannot honour) |
| `skills/lib/test_next_batch.py` | `~/.claude/skills/lib/test_next_batch.py` (120 cases on fixture trees built in `tmp`; carries no corpus and skips nothing) |
| `skills/lib/check_claude_home.py` | `~/.claude/skills/lib/check_claude_home.py` (refuses a python file that resolves `~/.claude` by climbing parents from `__file__`, which a git worktree breaks) |
| `skills/lib/check_issue_size.py` | `~/.claude/skills/lib/check_issue_size.py` (counts an issue file's acceptance criteria and refuses one bigger than any issue this pipeline has finished; the count replaces a judgement, and the docstring carries the measured spans it was chosen on) |
| `skills/lib/test_check_issue_size.py` | `~/.claude/skills/lib/test_check_issue_size.py` (23 cases on fixtures built in `tmp`; carries no corpus and skips nothing) |
| `skills/lib/rulings.py` | `~/.claude/skills/lib/rulings.py` (the rulings file and its reader, so a pass cannot queue a question the human has already answered; `check_queue_shard.py` imports it, and the `ruled` and `record` refusals are off without it) |
| `skills/lib/test_rulings.py` | `~/.claude/skills/lib/test_rulings.py` (85 cases on fixtures built in `tmp`; carries no corpus and skips nothing) |
| `skills/lib/sweep_parked.py` | `~/.claude/skills/lib/sweep_parked.py` (lists the parked issues that want a human's eye again — those past thirty days, and those some open issue now names as a blocker — so `parked` is a door rather than a deletion with a nicer name; it changes no file) |
| `skills/lib/test_sweep_parked.py` | `~/.claude/skills/lib/test_sweep_parked.py` (20 cases on fixtures built in `tmp`; carries no corpus and skips nothing) |
| `skills/lib/board.py` | `~/.claude/skills/lib/board.py` (draws the whole tracker as one self-contained page from the issue files and the run ledgers, generated the way `register.md` is generated and thrown away the same way; it calls `next_batch.schedule` rather than re-deriving the order, stores nothing and requests nothing) |
| `skills/lib/test_board.py` | `~/.claude/skills/lib/test_board.py` (46 cases on fixtures built in `tmp`; carries no corpus and skips nothing) |
| `skills/lib/test_check_claude_home.py` | `~/.claude/skills/lib/test_check_claude_home.py` |
| `skills/lib/check_issue_links.py` | `~/.claude/skills/lib/check_issue_links.py` (refuses a `[[link]]` in an issue file that names no issue) |
| `skills/lib/test_check_issue_links.py` | `~/.claude/skills/lib/test_check_issue_links.py` |
| `skills/lib/check_queue_shard.py` | `~/.claude/skills/lib/check_queue_shard.py` (refuses a queue item the daily brief can never retire, because its heading carries no backticked `q-` id) |
| `skills/lib/test_check_queue_shard.py` | `~/.claude/skills/lib/test_check_queue_shard.py` |
| `skills/lib/clean_worktrees.py` | `~/.claude/skills/lib/clean_worktrees.py` (removes the worktrees and branches a merge finished, and refuses every tree it cannot prove is finished: the main checkout, the tree it runs in, dirty, detached, a branch that is not an ancestor of the base ref, and a tree a live session holds) |
| `skills/lib/test_clean_worktrees.py` | `~/.claude/skills/lib/test_clean_worktrees.py` (15 cases, 13 of them about a refusal, on a real git fixture built in `tmp`; carries no corpus and skips nothing) |
| `skills/lib/set_level.py` | `~/.claude/skills/lib/set_level.py` (sets an issue's `Level:` from the paths it touches and the repo's risk file) |
| `skills/lib/test_set_level.py` | `~/.claude/skills/lib/test_set_level.py` (27 cases on fixtures built in `tmp`; one skips, because it reads a risk file this pack does not carry) |
| `skills/lib/check_overlap.py` | `~/.claude/skills/lib/check_overlap.py` (refuses a drafted issue that does not name each open issue whose paths it meets) |
| `skills/lib/test_check_overlap.py` | `~/.claude/skills/lib/test_check_overlap.py` (28 cases on fixtures built in `tmp`; carries no corpus and skips nothing) |
| `skills/lib/check_promotion.py` | `~/.claude/skills/lib/check_promotion.py` (refuses a promotion past half the week's closed issues, at the moment a human turns a register row into an issue file) |
| `skills/lib/test_check_promotion.py` | `~/.claude/skills/lib/test_check_promotion.py` (21 cases on fixtures built in `tmp`; carries no corpus and skips nothing) |
| `skills/lib/class_only_edit.py` | `~/.claude/skills/lib/class_only_edit.py` (decides whether a change to a file only edits styling class names) |
| `skills/lib/test_class_only_edit.py` | `~/.claude/skills/lib/test_class_only_edit.py` (75 cases on fixtures built in `tmp`; carries no corpus and skips nothing) |
| `skills/lib/retire_done_rows.py` | `~/.claude/skills/lib/retire_done_rows.py` (retires every done row of a register, so the register holds only the inbox; imports `run-issues/check_register_status.py`) |
| `skills/lib/test_retire_done_rows.py` | `~/.claude/skills/lib/test_retire_done_rows.py` (10 cases on fixtures built in `tmp`; carries no corpus and skips nothing) |
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

**`retry_brief.py` and its drill are withheld until the sync that takes `SKILL.md`
whole, and the reason is the pair rather than the script.** Step 7 of `SKILL.md` is
what calls it, and the published `SKILL.md` is about 120 lines behind the live copy
written by sessions this one did not run. Shipping the script alone gives a reader a
file nothing in the pack invokes; shipping the step that calls it means publishing
those other sessions' work in the same file, unread. That is one sync decision, not
two, and it is the human's. The drill travels with the script because it imports it.
Recorded 2026-09-13, from run `batch-d67136`.

**On 2026-09-29 both went out, in two steps.** The script went first, on rule 3. The
premise above was that nothing in the pack invokes `retry_brief.py`, and that stopped
being true when `charge_round.py` arrived: it imports `retry_brief` for the criterion
reader and the owned-text split, and the published gate briefs and `check_attempt_cap.py`
call `charge_round.py`. Later the same day the human lifted the hold on `SKILL.md`, and
it went out in the sync's second commit, read end to end beside the live copy. Every
reference in it to a withheld script or hook became a conditional that names the
author's file and says this pack does not ship it.

**Three things travel as part of a file rather than as a file, and the 2026-09-20 sync
records them here so a reader is not left comparing line counts.**

`skills/run-issues/decisions.md` withheld one section, "The retry brief states the
invariant", 56 lines, until 2026-09-29. It is the decision record for `retry_brief.py`,
and a decision record for a script nobody has is a reference to nothing. The script ships
now, so the section does too, and the file travels whole.

`skills/run-issues/test_skill_structure.py` carried 204 of its live copy's 238 cases while
`SKILL.md` was held, and 235 once it was published on 2026-09-29; the 2026-09-30 sync
brought it to 244 of 247, and the 2026-10-01 sync, which took the deleted downgrade case
out of both copies, to 243 of 246. It still holds four,
which grade the withheld `memory_dir.py` and a pending-actions file this pack does not
have; a published inverse, `TestCitationsResolveAnywhere`, asserts that no skill cites a
machine-local path. `test_model_map.py` held one case for a different reason: it pins
each agent file's effort to the skill table that spawns it, and the committed
`harden-issues-attacker.md` said `high` against its table's `medium` until the author
committed the live fix. It travels from 2026-09-30. Before 2026-09-29 every held case graded a sentence of `SKILL.md` that this pack did not
publish — 24 failures were measured by driving them against the published text — so
carrying them would have turned the pack red for every reader. The reasons for the cases
still held are written above the classes that keep them.
This is the same rule the two withheld isolation drills sit under: a drill that pins text
this pack does not ship grades a machine nobody else has.

`skills/run-compare/SKILL.md` publishes the `sizing` subcommand in full, and the way that
decision moved is worth the line. It was first held back on the manifest's own
skill-and-script rule, because the pack's `run_compare.py` had five subcommands and no
`sizing`, and the paragraph leans on `check_issue_size.py`. Both premises fell inside the
same sync: the script's sixth subcommand arrived with its own re-sync, and the size
counter was published. The rule did its work — the two went out together — and the
withholding it produced lasted only as long as the gap it described.

**`memory_dir.py` is withheld with its drill, and the reason is the file it points
at rather than the path it computes.** The mechanism is general and correct: slug a
repository's main checkout, resolved through `git rev-parse --git-common-dir` so that a
worktree answers for the repository owning it, into the matching directory under
`~/.claude/projects`, and print its `memory`. It exists because five files in the run
machinery had hard-coded one repository's answer, so a run on a second repository was
told to write a human's pending actions into the first one's list. But the two files it
can print are named in the CODE, not in prose: `--pending` and `--closed` append one
person's pending-actions filename, which rule 2 refuses and which nothing in this pack
has. Renaming them is not a scrub, because it changes what the script prints, and there
is nothing here for a new name to point at — `run-issues/SKILL.md` tells a reader to pass the
project's memory directory, if it keeps one, by hand. Its drill is
further away still: three of its cases read two named client checkouts by absolute path.
A later sync that takes the filename as an argument publishes both, and writing that
argument is authoring.

**`grade_transcripts.py` is withheld with its drill, and the first reason is an import
rather than a name.** It grades the Bash calls a repository's own sessions issued
against its allow list, reading the session directories under `~/.claude/projects`,
which is the reader's own directory and resolves anywhere. It cannot run here: it
imports `lib/memory_dir.py`, withheld above, and raises `ModuleNotFoundError` before it
parses an argument. Two more bar it. Its docstring's load-bearing claim — that the
quote-aware split lives in `check_permission_floor._outside_quotes` — is false of the
published floor, which carries no such function, and H3's rule that a claim must be true
of the published file is the right test for a script as well as a hook. And its report
prints a person's name on every run, in two lines a reader sees. The drill's only
real-corpus class is pinned to one absolute checkout.

**`check_run_isolation.py` is withheld, and the reason is the pair rather than the
pinning.** It refuses a run launch whose worktree has not claimed its own database, and
the fault under it is real anywhere: two suites that truncate every table between tests,
pointed at one database, wipe each other and read as regressions. Until
2026-09-29 the published `SKILL.md` carried no isolation step, so the script would have
been an exit-1 refuser nothing in this pack invokes. It carries the step now, with a
conditional where the live copy calls this script. What holds the script back today is
its text: the docstring tells the fault as one project's story, by name, from its first
line, and its drill's fixtures are that project's database names. Rewriting both is
authoring rather than scrubbing. Its drill is already withheld above, and a
refusing script whose test cannot run is worse evidence than no script.

**`run-isolation-2026-09-15.md` is withheld as a session record, which is a class this
map already names.** It is a design note written for one person to rule on, and it
argues with the shape he proposed. It names the author eight times, two products, one
database, three `scripts/*.mjs` files this pack does not ship, and one home-directory
env path in full. There is no scrub that leaves a skill file behind, only a rewrite. A
project's own steering file points readers at it, which is where it belongs.

**Two of the three files held back on 2026-09-20 went out on 2026-09-21, and the third
stays.** `hooks/rulings-write-guard.py` and its drill were minutes old at that sync and
nothing else was wrong with them, so this one published both. Five lines of the hook
named a person, three of them inside refusal text a reader sees, which is the scrub H2
already demands; one line named a product, and the drill named it once more. Both were
read end to end, and the hook was driven on a payload it must pass, one it must refuse
and one it cannot parse.

**`check_rulings_reach.py` stays withheld, and the reason has changed.** It is no longer
the age of the file. The heading it searches for carries a person's name, and it is a
literal in the code and in both of its refusals, so the name is what the tool matches on
rather than something the prose says. That is the `memory_dir.py` case again: renaming it
changes what the script finds, and nothing here defines a heading for a new name to match.
Its drill, `test_check_rulings_reach.py`, arrived after 2026-09-21 and is withheld with it,
because it drives a script this pack does not have. A later sync that takes the heading as an argument
publishes it, and writing that argument is authoring. `skills/harden-issues/SKILL.md`
carries the duty the script guards, and says in as many words that this pack ships no
refusal for it.

**`check_run_silences.py` is withheld with its drill, and the reason is the history it
reads.** It checks that a run's ledger records every charge the gates made, and to place a
ledger it reads the author's skills repository at fixed commits. A ledger fingerprinted
anywhere else is unreadable to it, and nothing in this pack calls it. Its drill pins four
real commits of that repository; 22 of its 24 cases failed when driven from another git
repository. A later sync that reads the fingerprint from the reader's own tree publishes
both, and writing that is authoring.

```withheld
~/.claude/skills/run-issues/test_run_isolation.py
~/.claude/skills/run-issues/check_run_silences.py
~/.claude/skills/run-issues/test_check_run_silences.py
~/.claude/skills/parallel-hunt/test_hunt_isolation.py
~/.claude/skills/run-issues/panel-review-*.md
~/.claude/skills/run-issues/workflow-redesign-*.md
~/.claude/skills/run-issues/harness/*
~/.claude/skills/run-issues/harness/fixture/*
~/.claude/skills/run-issues/harness/fixture/src/*
~/.claude/skills/run-issues/harness/fixture/test/*
~/.claude/skills/lib/memory_dir.py
~/.claude/skills/lib/test_memory_dir.py
~/.claude/skills/lib/check_rulings_reach.py
~/.claude/skills/lib/test_check_rulings_reach.py
~/.claude/skills/run-issues/grade_transcripts.py
~/.claude/skills/run-issues/test_grade_transcripts.py
~/.claude/skills/run-issues/check_run_isolation.py
~/.claude/skills/run-issues/run-isolation-2026-09-15.md
```

**Three tools that arrived after 2026-10-01 are withheld, and the reason is their text.**
`check_walk_closed.py` and the two hooks `fixed-sleep-guard.py` and `issue-size-guard.py`
each tell their fault as one project's story, by name, and their drills carry that
project's fixtures. Rewriting them is authoring rather than scrubbing. The published
`harden-issues/SKILL.md` names the walk check as a script this pack does not ship. Decided
in the 2026-10-04 sync; a later sync may publish them:

```withheld
~/.claude/skills/harden-issues/check_walk_closed.py
~/.claude/skills/harden-issues/test_check_walk_closed.py
~/.claude/hooks/fixed-sleep-guard.py
~/.claude/hooks/test_fixed_sleep_guard.py
~/.claude/hooks/issue-size-guard.py
~/.claude/hooks/test_issue_size_guard.py
```

**Two tools that arrived after 2026-10-07 wait, with their drills, for the sync that takes
the skill text calling them.** `check_overlap_rule.py` and its drill are named by the live
`harden-issues/SKILL.md`, and `mint_carved.py` and its drill by the live `run-issues/SKILL.md`; the
published copies of both skills predate them and call neither. The 2026-10-11 sync took
the suite wrapper alone, so publishing them now would ship scripts nothing here runs.
Decided in that sync; the sync that takes either `SKILL.md` publishes them:

```withheld
~/.claude/skills/harden-issues/check_overlap_rule.py
~/.claude/skills/harden-issues/test_check_overlap_rule.py
~/.claude/skills/run-issues/mint_carved.py
~/.claude/skills/run-issues/test_mint_carved.py
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
| `hooks/test_git_shared_state_guard.py` | `~/.claude/hooks/test_git_shared_state_guard.py` (79 behavioural cases against a real git fixture, mutation-tested, added 2026-09-08) |
| `hooks/run-issues-brief-cap.py` | `~/.claude/hooks/run-issues-brief-cap.py` (refuses a first-attempt implementer brief longer than the part that varies) |
| `hooks/test_run_issues_brief_cap.py` | `~/.claude/hooks/test_run_issues_brief_cap.py` |
| `hooks/run-issues-typecheck-gate.py` | `~/.claude/hooks/run-issues-typecheck-gate.py` (refuses a gate spawn while the run's own tree does not typecheck) |
| `hooks/test_run_issues_typecheck_gate.py` | `~/.claude/hooks/test_run_issues_typecheck_gate.py` |
| `hooks/gate-commit-guard.py` | `~/.claude/hooks/gate-commit-guard.py` (refuses a `git commit` by one of the adversarial gate roles; the runner commits, a gate reports) |
| `hooks/test_gate_commit_guard.py` | `~/.claude/hooks/test_gate_commit_guard.py` (21 cases on command strings, plus one pinning the guarded role list against `agents/`) |
| `hooks/machine-wide-kill-guard.py` | `~/.claude/hooks/machine-wide-kill-guard.py` (refuses a kill that selects processes by pattern rather than by pid) |
| `hooks/test_machine_wide_kill_guard.py` | `~/.claude/hooks/test_machine_wide_kill_guard.py` (19 cases on command strings alone; carries no corpus and skips nothing) |
| `hooks/rulings-write-guard.py` | `~/.claude/hooks/rulings-write-guard.py` (refuses a write that would leave an entry `rulings.py` cannot read, and a write that empties a rulings file holding entries) |
| `hooks/test_rulings_write_guard.py` | `~/.claude/hooks/test_rulings_write_guard.py` (14 cases, the malformed entry copied from the real one; rewritten under rule 3 to drive the hook beside it rather than one in the reader's `~/.claude/hooks`) |
| `hooks/run-issues-suite-gate.py` | `~/.claude/hooks/run-issues-suite-gate.py` (refuses a whole suite in a run that does not go through `run_suite.py` at a stage the caller owns) |
| `hooks/test_run_issues_suite_gate.py` | `~/.claude/hooks/test_run_issues_suite_gate.py` (56 cases; one skips where no `settings.json` sits beside `hooks/`, as in the pack) |
| `hooks/run-issues-wakeup-gate.py` | `~/.claude/hooks/run-issues-wakeup-gate.py` (refuses a `run-issues-*` spawn until the run's ledger names a wakeup cron made by this `claude` process) |
| `hooks/test_run_issues_wakeup_gate.py` | `~/.claude/hooks/test_run_issues_wakeup_gate.py` (25 cases; one skips where no `settings.json` sits beside `hooks/`, as in the pack) |
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

**That reasoning is now out of date, and the 2026-09-20 sync is what dated it.** Two
paragraphs above call rewriting an `AFK` refusal message to a role "authoring rather
than scrubbing", and that was measured before the pack had a precedent. It has four now.
`run-issues-foreground-gate.py`, `run-issues-brief-cap.py` and
`run-issues-typecheck-gate.py` each ship an `AFK` constant already rewritten to a role,
a published drill pins that wording, and `skills/run-issues/correction_brief.py` carries
the same sentence scrubbed the same way. Copying that substitution into a fourth hook is
following the pack, not authoring for it, which is why `gate-commit-guard.py` ships in
this sync. The message bar on the remaining withheld hooks therefore falls; what still
holds each of them back is its own test reading a real checkout, and that is the
sentence a later sync should act on.

**The same sync found the pack had been publishing the fault it withholds hooks for.**
Three scripts — `check_briefing_commands.py`, `citation_pass.py` and
`correction_close.py` — shipped a refusal reading "IT NEVER WAITS FOR <name>. He is AFK
for every run", with the person's first name in the message a reader sees, and three
drills carried the name in a method name. It had been public since those files were
first published. The scrub that fixed it was already in the pack, one directory away, in
`correction_brief.py`; the three now match it word for word. Two things let it through:
every earlier sweep matched one capitalisation, and none looked inside an identifier,
where `\b` does not fire against an underscore. A guard that enumerates the spellings it
forbids passes the spelling nobody listed — which is the rule `steering/coderules.md`
states, met here in this map's own files.

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

**`pilot-database-guard.py` arrived on 2026-09-12 and is withheld, with its test.** It
refuses a Bash command that writes to one named customer-facing database, and the project
ref is in the refusal message, in the docstring and in the matching itself. H2 refuses a
message naming a repo, and rule 2 refuses a client-identifying name anywhere in this pack.
There is a general hook inside it — refuse an unreadable write at a production database,
name the safe one, and let reads past — and a later sync could publish that, reading both
refs from the environment. Rewriting it that way is authoring rather than scrubbing.

**Its matching is worth a reader's attention even though the file is withheld**, because
the same shape will appear in whatever replaces it. It refused a `grep` during this very
sync: the command carried the project ref as part of a search pattern, no SQL was involved,
and the hook could not tell a search for the string from a write to the thing. A guard that
matches a bare identifier anywhere in a command line refuses reading ABOUT the database as
readily as writing TO it.

**That was fixed the same day, and how it was fixed is the part worth copying.** The fault
was one conflated answer, not the matching. The hook asked "can I read this command's SQL?"
and refused when it could not — but "could not" was covering two different lines: a database
command whose statement is hidden in a file, which must be refused, and a command that is
not a database command at all, which was never this hook's business. The fix asks a second
question first — is there a road to a database in this line, meaning a client the hook can
name or a connection URI — and where there is none it passes without ever looking at the
SQL.

**The fix that was tried first is the instructive one, because it is the one most readers
will reach for and it is wrong.** It taught the hook which commands are searches: an
allowlist of text tools, the command split into pipeline segments, a tokeniser that knows a
quoted `a|b` from a shell pipe. That is a shell parser, and a parser inside a security
control is a new bypass road — whatever it mis-reads as a search walks through. It had a
hole within the hour: the tokeniser reads a newline as whitespace where the shell reads it
as a new command, so a `grep` on one line and a `psql ... delete` on the next passed as a
single harmless search. Ask what roads a command opens; never ask what a command is.

**A second road opens no connection at all, and the same shape closes it.** Printing the
connection string puts a live credential in a transcript, and a transcript outlives the
session. Asking which commands print a secret would be a parser again; asking whether the line
expands the variable that holds one is a substring. So `echo $PROD_SUPABASE_DB_URL` is refused
while `grep -rn PROD_SUPABASE_DB_URL scripts/` is not, and the whole difference is the `$`.

**The denylist has a gap, and the published successor should carry it in its own words.** A
client the list does not name is a client the hook does not see — a bare `./scripts/migrate.sh`,
a compiled binary, a tool nobody has used yet. Closing that needs the position of a word in the
command line, which is the parser. The gap is a consequence of refusing to guess, not a fault
in the guard, and naming it is what lets a reader judge the trade rather than inherit it.

**Three hooks and a reader that arrived after 2026-09-21 are withheld, and the reason is
an import rather than a message.** `gate-issue-write-guard.py` refuses a subagent that
creates an issue file or writes a gate's verdict into one. `run-issues-risk-path-guard.py`
refuses a light issue's write to a path the repo's risk file names, and it reads that file
through `risk_path_reader.py`. Both guards import `gate-source-write-guard.py`, which is
withheld below, and through it `generated-file-guard.py`. Without them the gate-issue guard
fails open on every call, so it would ship as a hook that refuses nothing. The risk-path
guard is also unregistered in the author's own setup until a planned change is built, and
a pack should not ship a control its author has switched off. The reader goes with the
guard, because nothing else imports it. Both drills drive a withheld hook, and one of them
asserts a file exists at the author's absolute hooks path. The briefs and skill text that
name either guard now say what it refuses and that this pack does not ship it.

`run-issues-suite-gate.py` arrived in the same stretch and ships. Its refusal cites step 5
of `run-issues/SKILL.md` for the coverage re-run after a correction round. That was false
of the pack for the few hours `SKILL.md` stayed held, and true again once it was published.

**`headless-chrome-guard.py` arrived on 2026-09-30 and is withheld with its drill, and the
reason is the road its refusal sends a reader down.** It refuses a Bash command that runs a
Chrome binary from inside an app bundle without four flags: the two that keep Chrome off the
macOS keychain, and the two that keep it off the media keys. The fault is real on any Mac
running agents in a sandbox. But the refusal's only remedy is `~/.claude/bin/headless-chrome`,
a wrapper script in the author's tool directory that this pack does not ship, and the drill
asserts that path is in the message. A refusal that names a file the reader does not have is
the stale line H3 exists for, and rule 3 bars the dependency. The message also names a person
and a date, which H2 refuses. Shipping the wrapper beside it would open a `bin/` class this map
does not have, and rewriting the refusal to list the flags instead is authoring rather than
scrubbing. `skills/lib/test_board.py` carries the four flags in its own Chrome call, so the
fix itself is public.

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
~/.claude/hooks/pilot-database-guard.py
~/.claude/hooks/test_pilot_database_guard.py
~/.claude/hooks/machine-preflight.py
~/.claude/hooks/test_machine_preflight.py
~/.claude/hooks/heavy-run-version.pin
~/.claude/hooks/browser-budget.py
~/.claude/hooks/worktree-snapshot-notice.py
~/.claude/hooks/test_worktree_snapshot_notice.py
~/.claude/hooks/worktree-base-drift.py
~/.claude/hooks/test_worktree_base_drift.py
~/.claude/hooks/test_settings_env.py
~/.claude/hooks/TOOL-SET-PROBE.md
~/.claude/hooks/gate-issue-write-guard.py
~/.claude/hooks/test_gate_issue_write_guard.py
~/.claude/hooks/run-issues-risk-path-guard.py
~/.claude/hooks/test_run_issues_risk_path_guard.py
~/.claude/hooks/risk_path_reader.py
~/.claude/hooks/headless-chrome-guard.py
~/.claude/hooks/test_headless_chrome_guard.py
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

**But diff the published copy against the live one for every file you are about to
publish, and read it as a scrub list rather than a change list.** The two instruments
answer different questions. The tag diff says WHAT CHANGED upstream; it cannot say that
a scrub this pack already made has been undone, because upstream the undoing is not a
change to anything — it is just how a live file was always written.

That is not hypothetical. On 2026-09-13 three files came up for their second sync and
all three had regressed scrubs made on 2026-09-12: a person's name, two product names,
a client checkout standing in as a fixture name, and three shard id prefixes. Nothing
was reverted and nobody was careless; a session editing a live file has no reason to
keep this pack's wording, and the neutral version exists only here.

So a file with an existing row is not a copy job. Read the published copy beside the
live one, take the new facts, and keep the scrub you already own. `check_queue_shard.py`
that day needed exactly one new sentence out of a paragraph the live copy had rewritten
whole. A scrub does not stay done.

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
