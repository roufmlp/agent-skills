# Orderflow drift and alignment facts (repo ~/code/orderflow, HEAD 38bfbede1, 2653 commits, 2026-09-09 to 2026-10-31)

## 1. Alignment mechanisms
CI (.github/workflows/ci.yml, on push to main and every PR) runs: npm run lint, npm run typecheck, npm test, npm run build. e2e.yml runs npm run e2e but its flows skip on CI (no DB or object store). No pre-push hook: .git/hooks holds only samples, core.hooksPath is empty, no .husky.

| Item | Lines | Kind | Runs how |
|---|---|---|---|
| eslint.control-ban.mjs (added d74edeac9, 2026-09-12) | 182 | REFUSES. 8 banned raw forms (e.g. raw input type=date) via no-restricted-syntax, error severity, allowed only in the owning src/controls/<module> dir | `npm run lint` (CI) and in the editor |
| tests/build-checks/*.test.ts | 69 test files | REFUSES. Greps/scans of src: design-values (no literal colours/lengths outside src/styles/tokens), one-button, one-status-chip, one-floating-action, one-upload-field, one-readers-move, one-choice-control, status-literals, src-import-boundary, no-eslint-disable, frozen-prototypes, prototype-pairs, patterns-file, etc. | `npm test` (vitest, CI). Whole suite ~197 s at 8 workers (vitest.config.ts comment) |
| tests/scaffold/ (server-boundary, admin-client-boundary, supabase-auth-boundary, phone-first, no-shared-store) | ~25 files | REFUSES | `npm test` |
| docs/patterns.md | 776 | PROSE an agent must read, with a graded shell. Approved entries must name a test; patterns-file.test.ts checks each quoted phrase sits on the cited line. Only 17 entries, 5 "Not approved" mentions. Nothing refuses a shape that is absent from it | read by coderules rule 6; test runs in `npm test`. CLAUDE.md does not point to it |
| docs/visual-direction.md (8070ff769, 2026-09-09) | 97 | PROSE. Colour, type, spacing. Not machine-checked itself; its token values are checked by design-values/token-contrast/tokens-parity tests | read only |
| docs/phone-first.md (f0489bb80, 2026-09-12) | 48 | PROSE; two values (viewport meta, 390 px Playwright viewport) held by tests/scaffold/phone-first.test.ts | test in `npm test` |
| docs/agents/prototype-fidelity.md (84a568f63, 2026-10-04) | 461 | PROSE rulebook + a measuring tool. Severity classes S1-S6 SMALL, L1-L5 LARGE, rest MEDIUM; "pixel diffing was turned down" | tool: `npm run fidelity:shots -- <ROW>` (manual, by implementer; builds+serves app, "a few minutes"). Not in CI |
| reference/prototypes/{operations,sales,admin}/ | 3 folders of plain HTML/JS | FROZEN SPEC. MANIFEST.sha256 per folder; tests/build-checks/frozen-prototypes.test.ts fails on any edit | `npm test` |
| tests/build-checks/prototype-pairs.test.ts | - | REFUSES a merge when a `done` issue claims a screen row with no image pair, or with a difference list that is unfilled or cites no real ruling. Checks existence and citations, not pixels or visual match | `npm test` |
| CONTEXT.md (ff2f576f0, 2026-09-09) | 506 | PROSE glossary ("Avoid" words). No implementation detail. Not machine-checked (step-words.test.ts, tap-words.test.ts check some words) | read only |
| docs/adr/ | 2 files: 0001 rules-refuse-in-the-model, 0002 one-component-one-place | PROSE, but each ADR names its enforcing check. ADR 2 = raw-control ban (eslint) + design-values (vitest) | via those checks |
| docs/architecture-review-2026-09-30.md | 491 | PROSE: 7 candidates to deepen modules. Not a module map | read only |
| CLAUDE.md | 172 | PROSE. Points to prototype-fidelity.md only; no pointer to patterns.md or visual-direction.md (grep) | read only |
| rights-grep, transaction-boundary, store-outside-transaction, server-takes-no-client-value, citation-form | in build-checks | REFUSES (ADR 1: permissions/money gates refuse in the model) | `npm test` |

## 2. Evidence of drift (counts)
- `git log --oneline | grep -iE "align|consisten|duplicat|match the prototype|fidelity|unify|one place|second copy|drift|polish"`: 27 commits of 2653.
- Issue files: 755 in .scratch/orderflow-v1/issues/; 651 `Status: done`. 57 filenames match align/consist/duplic/unify/one-/match/fidelity/prototype; 223 files mention "fidelity" or "matches the prototype".
- Fidelity machinery records: 290 captured screen rows (113 OPS, 108 SAL, 63 ADM) in .scratch/orderflow-v1/fidelity/; 284 differences.md filled; 2175 difference rows in them (each a text/style gap needing a ruling or a fix).
- The 5 clearest:
  1. UI audit, 2026-09-25 (.scratch/orderflow-v1/ui-audit-2026-09-25/README.md): five auditors found 126 faults across 18 pages, merged into 15 issues (220-254). Includes "Config lists use six row shapes for one job" (issue 232) and "focus is drawn three ways" (issue 230).
  2. ADR 2 (af311e5da, 2026-09-12): the prototype held four custom calendars plus seven raw `<input type="date">`; "the choice was made seven times by whoever wrote the field". Led to eslint.control-ban. Issue 226 / 4a404e25a "Draw every date as one field".
  3. Duplicate-fold pass, 2026-09-25 (ui-audit-2026-09-25/duplicates.md, commit 50b02c329): audit issues 220-254 were written without reading 29 older open issues; 16 older/new pairs plus 2 inside the new set would build the same thing twice or two ways (e.g. issue 155 vs 227, the same missing-file fault fixed at two layers). 5214229f6: issue 137 built, 118 closed as duplicate.
  4. Architecture review, 2026-09-30 (docs/architecture-review-2026-09-30.md): the upload order is hand-written in about 10 server actions, noteStorageWrite called at 15 sites; "Two copies already disagree" on what to do when the storage meter cannot be read. Candidate 3: status names/sets in many modules -> issue 300 "One home for status names" (done) with a check refusing a new copy. Same pattern: issue 394 one-readers-move predicate (7b39457ae), 424 "one module words every chip and next step", 512 "three screens choose the sales layout by one rule" (the finale of run batch-4a2388 had accepted "three rules as built").
  5. Catch-up fidelity issues AFTER the screens were built: 438 papers, 439 and 476b bill pages, 440 customer page, 442 report screens, each "match the prototype" (ed592e26d, 18aa34bea, fdf114d92, f1bae5923, 6e74b9b8e; 2026-10-08 to 2026-10-11). Also 0e878a023 "Recapture every fidelity row after 577 and rule its differences (issue 592)": one issue's change moved other rows. Own record in prototype-fidelity.md: "8 of the 16 rejects since 4 October were screen differences found by eye, a new set each round".
- Why: prototype-fidelity.md "Why this exists": the audit of 25 September found 126 faults; "Nothing carried the look: the prototype code sat on branches that never merge".

## 3. Did refusing checks catch drift?
- eslint.control-ban.mjs: added d74edeac9 (2026-09-12) as "Issue 01b: the three build checks fail the build, never warn", before any control existed; ADR 2 (accepted 2026-09-12) set it. Extended later with each shared control (4a404e25a date 2026-09, 4814323ea page title, issue 235c). Drills in fixtures/build-checks prove it fires. I found no log of a build it failed in production use; it is a preventive list that grows when someone builds the control (ADR 2 rule 5: "A new shared control is added to this list when it is built").
- Sequence matters: one-* checks arrived AFTER the drift: one-floating-action ce481a6b1 (09-18), one-button 3758972ff (09-26, issue 227c), one-choice-control 2c9762ee0 and one-status-chip eded79ad4 (09-27), one-readers-move 7b39457ae (10-04), one-upload-field 860a6681a (10-15, issue 577). Each was added when the drift was already in the tree and fixed by the issue that built the check.
- Fidelity: prototype-fidelity.md arrived 2026-10-04, 25 days after the repo began. Measurement .scratch/orderflow-v1/fidelity-measure-2026-10-05/README.md: row OPS-S07 gave 65 texts owing a row before the capture rewrite; after it 43 texts (19 LARGE, 24 MEDIUM) and 85 style lines (43 MEDIUM, 42 SMALL). So the tool found real failures; it feeds a human/agent difference list, and the check only refuses missing lists/citations. A MEDIUM/LARGE difference that stays needs a cited ruling, so the 2175 difference rows are mostly ruled-in exceptions. Rule: "A screen difference never blocks an issue" (at attempt cap it lands short).
- prototype-pairs.test.ts has CAPTURES_BEFORE_CEILING = 0 (a ratchet).

## 4. Prototype pairs
- Prototypes: reference/prototypes/{operations,sales,admin}/, plain HTML/CSS/JS, frozen with MANIFEST.sha256. No screenshots live there.
- Pairs live in .scratch/orderflow-v1/fidelity/<ROW>/ : prototype-390.png, built-390.png, prototype-1280.png, built-1280.png, words.md, styles.md, differences.md. 290 row folders, 2771 PNGs, 317 MB, tracked in git (.scratch/ has 12092 tracked files).
- Rows come from a "Screen inventory" table in each PRD (.scratch/orderflow-v1/PRD-{sales,operations,admin}.md): Row id, state, prototype view, built page, widths.
- Comparison: NOT pixel diff (turned down). The script drives both pages in Playwright (e2e/fidelity-shots.spec.ts, scripts/prototype-shots.ts, scripts/lib/prototype-fidelity.ts), extracts text, computed style, painted boxes, and writes words.md/styles.md with each difference classed SMALL/MEDIUM/LARGE (lib figures; tests/scripts/prototype-fidelity.test.ts). Agent reads the lists, fixes, recaptures, fills differences.md with rulings. Images are for human/agent eyes.
- Run time: per row builds and serves the app, "a few minutes" (prototype-fidelity.md; spec header "takes minutes"); `--origin` uses a running dev server; `--prototype-only` needs no app. Not run in CI. CI runs only prototype-pairs.test.ts (file existence/citations) inside the ~197 s `npm test`.

## 5. Module boundaries
- No written module map. No dependency-cruiser; package.json has no import-lint plugin; eslint.config.mjs has no no-restricted-imports (only eqeqeq, no-var, prefer-const, no-duplicate-imports, plus the control ban). Boundaries are enforced by custom vitest tests instead:
  - tests/build-checks/src-import-boundary.test.ts (dd3bef0d7, 2026-09-13): src may import only relative paths inside src/ or declared packages (closed rule). Created after src/model imported from tests/harness unnoticed by lint, build and deploy.
  - tests/scaffold/server-boundary.test.ts: browser-reachable code cannot reach the database (transitive walk). admin-client-boundary, supabase-auth-boundary, storage-crossing, storage-reach, transaction-boundary, store-outside-transaction, server-takes-no-client-value.
  - tests/scaffold/module-imports.ts and database-modules.ts are the shared walkers.
  - No test found that stops src/app from importing a control's internals instead of its index, or model files from importing each other freely.
- src/ layout, top two levels:
  - src/app/ : (signed-in), api, auth, dev, fonts, login, plus layout/globals/error/not-found files
  - src/controls/ : action, config-list, date, field, file, layout, money, picker, popup, refusal, segments, status-chip, storage, undo (shared UI controls; each owns its raw form)
  - src/lib/ : db, documents, draft, http, problem-report-outbox, push, sign-in, storage, plus rate-limit and misc files
  - src/model/ : flat list of domain files (accept, assign, booking, bill-*, brief-*, cancel, catalogue, ...) plus views/
  - src/styles/ : tokens.css, tokens.ts
- Closest to a map: CONTEXT.md (glossary, no code) and docs/architecture-review-2026-09-30.md (7 deepen-module candidates, written after the code existed).
