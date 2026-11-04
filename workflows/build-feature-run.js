export const meta = {
  name: 'build-feature-run',
  description: 'Build an approved feature plan: each change note through its own implementer, verifier and reviewer, three notes at once, one merger between them, then the final check and the merge into local main',
  phases: [
    { title: 'Notes', detail: 'one implementer, verifier and reviewer per note, three notes at once' },
    { title: 'Final check', detail: 'the whole feature: final verifier and final reviewer, one fix round' },
    { title: 'Merge', detail: 'fast-forward only, as a --no-ff merge commit, through the hooks' },
  ],
}

// The run half of /build-feature. The session that starts it computes `args`
// with `python3 ~/.claude/skills/workflow/lib/feature_run.py args <feature> --tree <feature worktree>`
// and passes that JSON here; this script has no filesystem, so every path and
// every note row comes from there. The seven roles are the agent files
// `~/.claude/skills/workflow/agents/build-feature-<role>.md`; `agentType` takes each file's
// model and effort, and `args.roles[role].override` replaces them for a trial.
// `changes/<feature>/report.md` on the feature branch is the ledger: the merger
// writes it, and a later start reads it through feature_run.py.

const SKILLS = '~/.claude/skills/workflow'
const AT_ONCE = 3
const MAX_STRIKES = 3

const feature = args.feature
const notes = args.notes.map(n => ({ ...n, requeued: false, checked: false, reports: [], decide: [], defaults: [], edits: [] }))
const byNumber = Object.fromEntries(notes.map(n => [n.number, n]))
const strikesByRole = { implementer: 0, verifier: 0, reviewer: 0, 'note-checker': 0, merger: 0, 'final-verifier': 0, 'final-reviewer': 0, ...((args.earlier || {}).strikes || {}) }
let halted = null // the reason no further note starts
let finalState = 'stopped'
// An earlier run's lines in the three report parts a restart keeps; the
// session's feature_run.py read them from the report.
const earlier = { defaults: [], edits: [], final: [], ...(args.earlier || {}) }
let finalLines = [...earlier.final] // the `## Final check` lines, one per final role run
let mergeCommit = null

// ── helpers ────────────────────────────────────────────────────────────────

// Every role answers in a typed form, not in prose: `agent()` with a schema
// makes the runtime ask the role for these fields and refuse an answer that
// does not fit, before this script sees it. In the rehearsal the script read
// the verdict word out of the message text, found PASS in a reject's third
// line ("All 4 tests pass now"), and merged a rejected note. The long report
// still goes to the file the prompt names; the form carries the decision.
const LINES = { type: 'array', items: { type: 'string' } }
const VERDICT = {
  type: 'object',
  properties: {
    verdict: { enum: ['PASS', 'REJECT'], description: 'REJECT when any step or ground failed' },
    line: { type: 'string', description: 'one line: the verdict and the first ground, or "all steps passed"' },
  },
  required: ['verdict', 'line'],
}
const FINAL_VERDICT = {
  type: 'object',
  properties: {
    verdict: { enum: ['PASS', 'FINDINGS'] },
    line: { type: 'string', description: 'one line: the verdict and the steps or findings that failed, or "all steps passed"' },
  },
  required: ['verdict', 'line'],
}
const BUILT = {
  type: 'object',
  properties: {
    line: { type: 'string', description: 'one line: what was built and the commit' },
    edits: { ...LINES, description: 'Done-check edits: one line per done-check file edited, with what changed; empty when none' },
    defaults: { ...LINES, description: 'Defaults taken: one line each; empty when none' },
    keeps: { ...LINES, description: 'the keeps: test titles; empty when none' },
    stopped: { type: 'string', description: 'empty unless the note stops on a question for Abdul: then "stopped: <why>"' },
  },
  required: ['line', 'edits', 'defaults', 'keeps', 'stopped'],
}
const CHECKED = {
  type: 'object',
  properties: {
    outcome: { enum: ['corrected', 'sound', 'stopped'] },
    line: { type: 'string', description: 'the first line of the report: "Corrected: ...", "Sound: ..." or "Stopped: ..."' },
  },
  required: ['outcome', 'line'],
}
const MERGED = {
  type: 'object',
  properties: {
    outcome: { enum: ['done', 'nothing', 'conflict', 'refused', 'main moved', 'error'], description: 'done when the job made its commit or printed its sha; nothing when there was nothing to commit' },
    commit: { type: 'string', description: 'the full sha the job asks for (a base, a HEAD or the commit made); empty when there is none' },
    line: { type: 'string', description: 'one line: the job and its commit, or the Conflict:, REFUSED: or Error: line quoted' },
  },
  required: ['outcome', 'commit', 'line'],
}
const SHA = /^[0-9a-f]{7,40}$/i

// The sha a merger job answered with, when it is one.
function shaOf(out) {
  const sha = String((out && out.commit) || '').trim()
  return SHA.test(sha) ? sha : null
}

function stateOf(number) {
  return (byNumber[number] || {}).state || 'missing'
}

function isMerged(n) {
  return n.state.startsWith('merged')
}

function linesOrNone(lines) {
  return lines.length ? lines : ['none']
}

function rowsTable() {
  const rows = notes.map(n => `| ${n.number} | ${n.state} | ${n.strikes} | ${n.attempts} | ${n.last_report || ''} |`)
  return ['| Note | State | Strikes | Attempts | Last report |', '| --- | --- | --- | --- | --- |', ...rows].join('\n')
}

function rolesTable() {
  return ['| Role | Model | Effort | Tokens | Cost | Strikes |', '| --- | --- | --- | --- | --- | --- |',
    ...Object.keys(args.roles).map(r => `| ${r} | ${args.roles[r].model} | ${args.roles[r].effort} | | | ${strikesByRole[r] || 0} |`)].join('\n')
}

// One agent spawn. Returns the role's typed answer, or null when the agent
// returned nothing (the user skipped it, the usage limit was hit a third time,
// or an API error outlasted the runtime's own retries).
async function run(role, prompt, label, phase, schema) {
  const opts = { label, agentType: 'workflow:build-feature-' + role, phase, schema }
  const setting = args.roles[role] || {}
  if (setting.override) { opts.model = setting.model; opts.effort = setting.effort }
  let out = null
  try { out = await agent(prompt, opts) } catch (err) { log(`${label}: ${String(err).slice(0, 200)}`) }
  if (out === null || out === undefined || typeof out !== 'object') return null
  return out
}

// The same, with one retry, for the roles that have no note to requeue.
async function runAgain(role, prompt, label, phase, schema) {
  const first = await run(role, prompt, label, phase, schema)
  if (first !== null) return first
  log(`${label}: no result, one retry`)
  return run(role, prompt, label + ' (retry)', phase, schema)
}

// Every merger job goes through one queue: the feature worktree takes one
// merge at a time, and the report has one writer.
let mergerQueue = Promise.resolve()
function merger(job, body, label, phase) {
  const prompt = [
    `Feature worktree: ${args.tree} (branch feature/${feature})`,
    `Feature: ${feature}`,
    `Main checkout: ${args.repo} (branch ${args.main})`,
    `Job: ${job}`,
    '',
    body,
  ].join('\n')
  const next = mergerQueue.then(() => runAgain('merger', prompt, label, phase, MERGED))
  mergerQueue = next.catch(() => {})
  return next
}

function reportBody(state, extra) {
  return [
    'Write the whole report at changes/' + feature + '/report.md in the feature worktree, in the shape of ' + SKILLS + '/templates/report.md, and commit it as `report: ' + feature + ' ' + state + '`.',
    `Started: ${args.started}`,
    `State: ${state}`,
    'Time: the `Run:` line under ## Time reads from Started to the clock now (`date "+%Y-%m-%d %H:%M"`), with the hours between.',
    '',
    'The notes table, exactly these rows:',
    rowsTable(),
    '',
    'The roles table (tokens and cost are filled in after the run; leave those cells empty):',
    rolesTable(),
    '',
    'Done-check edits, one line per edit with its note number (an earlier run\'s lines first):',
    ...linesOrNone([...earlier.edits, ...notes.flatMap(n => n.edits.map(l => `${n.number}: ${l}`))]),
    '',
    'Defaults taken, one line each with its note number (an earlier run\'s lines first):',
    ...linesOrNone([...earlier.defaults, ...notes.flatMap(n => n.defaults.map(l => `${n.number}: ${l}`))]),
    '',
    'Decide, one line per question the run put under "Decide" in ~/.claude/pending.md:',
    ...(notes.flatMap(n => n.decide.map(l => `${n.number}: ${l}`)).length ? notes.flatMap(n => n.decide.map(l => `${n.number}: ${l}`)) : ['none']),
    '',
    ...(extra || []),
  ].join('\n')
}

function finalParts() {
  return [
    'Final check, one line each:',
    ...(finalLines.length ? finalLines : ['not run: a note failed, stopped or waits']),
    '',
    `Screens: copy the page at changes/${feature}/screens.md into the report's ## Screens part when the final verifier wrote it; otherwise write "none".`,
  ]
}

// ── one note ───────────────────────────────────────────────────────────────

async function prepareWorktree(n) {
  const body = [
    `Make the worktree for note ${n.number}: path ${n.worktree}, branch ${n.branch}, from the current feature branch.`,
    `Fresh: ${n.fresh ? 'yes; the session removed the old worktree and branch before the run' : 'no; if the worktree exists, keep it as it is'}.`,
    '',
    'Steps, each a command run through Bash:',
    `1. If Fresh is yes and the worktree exists, stop: answer outcome error with line "worktree ${n.worktree} still exists; the session removes a fresh note's worktree in step 2 of the skill". Never run \`git worktree remove\` yourself: the auto-mode classifier refuses \`--force\` as irreversible (measured 2026-11-04), and the session does the removal. If Fresh is no and the worktree exists, go to step 4.`,
    `2. \`git -C ${args.repo} worktree add ${n.worktree} -b ${n.branch} feature/${feature}\`; when the branch already exists with no worktree, \`git -C ${args.repo} worktree add ${n.worktree} ${n.branch}\` instead. Never \`git checkout -b\`; the guard refuses it.`,
    `3. Give the tree what it needs to run: \`cp -c -R ${args.repo}/node_modules ${n.worktree}/node_modules\` (an APFS clone; plain \`cp -R\` if -c fails), \`cp ${args.repo}/.env.local ${n.worktree}/.env.local\` when that file exists, then claim a database the way the product's .claude/run-isolation.json says, in the worktree: \`node scripts/run-db.mjs claim --batch ${args.batch} --tree ${n.worktree}\`. Skip a step whose file or script the product does not have, and say so.`,
    `4. Print the base: \`git -C ${n.worktree} merge-base feature/${feature} ${n.branch}\`.`,
    '',
    'Answer: outcome done with commit the base sha (step 4) and a line naming the tree and any step skipped; on a failure outcome error with the command and its output in the line.',
  ].join('\n')
  const out = await merger('worktree', body, `note ${n.number}: worktree`, 'Notes')
  if (out === null) return { error: 'merger returned no result' }
  const base = out.outcome === 'done' ? shaOf(out) : null
  if (!base) return { error: out.line }
  return { base }
}

function implementerPrompt(n, base) {
  return [
    `Tree: ${n.worktree} (branch ${n.branch})`,
    `Feature: ${feature}`,
    `Note: ${n.number}, at changes/${feature}/${n.path.split('/').pop()}`,
    `Base commit: ${base}`,
    `Attempt: ${n.attempts} of ${MAX_STRIKES}`,
    `Reject reports: ${n.reports.length ? n.reports.join(', ') : 'none'}`,
    n.checked ? `The note checker read the note after strike two; its report is ${n.reports[n.reports.length - 1]}. Read it first.` : '',
  ].filter(Boolean).join('\n')
}

function gatePrompt(n, base, reportPath, extra) {
  return [
    `Tree: ${n.worktree} (branch ${n.branch})`,
    `Feature: ${feature}`,
    `Note: ${n.number}, at changes/${feature}/${n.path.split('/').pop()}`,
    `Base commit: ${base}`,
    `Attempt: ${n.attempts}`,
    `Report path: ${reportPath}`,
    ...(extra || []),
  ].join('\n')
}

// A strike: record the report, and at the second strike spawn the note checker.
async function strike(n, role, reportPath) {
  n.strikes += 1
  strikesByRole[role] += 1
  n.last_report = reportPath
  if (!n.reports.includes(reportPath)) n.reports.push(reportPath)
  log(`note ${n.number}: strike ${n.strikes} (${role})`)
  if (n.strikes !== 2 || n.checked) return 'again'
  n.checked = true
  const checkPath = `${args.reports}/${n.number}-note-checker.md`
  const prompt = [
    `Tree: ${n.worktree} (branch ${n.branch})`,
    `Feature: ${feature}`,
    `Note: ${n.number}, at changes/${feature}/${n.path.split('/').pop()}`,
    `Reject report 1: ${n.reports[0]}`,
    `Reject report 2: ${n.reports[n.reports.length - 1]}`,
    `Report path: ${checkPath}`,
  ].join('\n')
  const out = await runAgain('note-checker', prompt, `note ${n.number}: note checker`, 'Notes', CHECKED)
  if (out === null) return 'stop:note-checker returned no result'
  n.reports.push(checkPath)
  if (out.outcome === 'stopped') { n.decide.push(out.line); return 'stop:' + out.line.replace(/^stopped:\s*/i, '') }
  if (out.outcome === 'corrected') { n.defaults.push(out.line); log(`note ${n.number}: ${out.line}`) }
  return 'again'
}

async function runNote(n) {
  n.state = 'running'
  let fresh = n.fresh
  while (n.strikes < MAX_STRIKES) {
    n.attempts += 1
    const ready = await prepareWorktree({ ...n, fresh })
    fresh = false
    if (ready.error) { n.state = `stopped: worktree: ${ready.error.slice(0, 120)}`; return }
    const base = ready.base
    const tag = `${n.number}-attempt-${n.attempts}`

    const built = await run('implementer', implementerPrompt(n, base), `note ${n.number}: implementer ${n.attempts}`, 'Notes', BUILT)
    if (built === null) { n.attempts -= 1; return requeue(n, 'implementer') }
    n.edits.push(...built.edits)
    n.defaults.push(...built.defaults)
    const stopped = String(built.stopped || '').trim()
    if (stopped) { n.state = /^stopped:/i.test(stopped) ? stopped : `stopped: ${stopped}`; n.decide.push(stopped); return }

    const verifyPath = `${args.reports}/${tag}-verifier.md`
    const verified = await run('verifier', gatePrompt(n, base, verifyPath), `note ${n.number}: verifier ${n.attempts}`, 'Notes', VERDICT)
    if (verified === null) { n.attempts -= 1; return requeue(n, 'verifier') }
    if (verified.verdict !== 'PASS') {
      const next = await strike(n, 'verifier', verifyPath)
      if (next.startsWith('stop:')) { n.state = `stopped: ${next.slice(5)}`; return }
      continue
    }

    const reviewPath = `${args.reports}/${tag}-reviewer.md`
    const keeps = built.keeps
    const reviewed = await run('reviewer', gatePrompt(n, base, reviewPath, [
      `Done-check edits from the implementer: ${n.edits.length ? n.edits.join('; ') : 'none'}`,
      `keeps: titles: ${keeps.length ? keeps.join('; ') : 'none'}`,
    ]), `note ${n.number}: reviewer ${n.attempts}`, 'Notes', VERDICT)
    if (reviewed === null) { n.attempts -= 1; return requeue(n, 'reviewer') }
    if (reviewed.verdict !== 'PASS') {
      const next = await strike(n, 'reviewer', reviewPath)
      if (next.startsWith('stop:')) { n.state = `stopped: ${next.slice(5)}`; return }
      continue
    }

    const mergePath = `${args.reports}/${tag}-merger.md`
    const merged = await merger('note', [
      `Note: ${n.number}, branch ${n.branch}, worktree ${n.worktree}.`,
      'Renumber its migrations, merge the branch into the feature worktree with `git merge --no-ff` (a cut note is reverted by `git revert -m 1`, which needs a merge commit with two parents), set its row and commit the report as the job says.',
      'The notes table today, for the rows you do not own:',
      rowsTable(),
      `Answer: outcome done with commit the full sha of the merge commit on success; outcome conflict or refused otherwise, with the \`Conflict: <files>\` or \`REFUSED:\` line as the line. Write the same to ${mergePath}.`,
    ].join('\n'), `note ${n.number}: merger`, 'Notes')
    if (merged === null) { n.attempts -= 1; return requeue(n, 'merger') }
    const sha = merged.outcome === 'done' ? shaOf(merged) : null
    if (!sha) {
      const next = await strike(n, 'merger', mergePath)
      if (next.startsWith('stop:')) { n.state = `stopped: ${next.slice(5)}`; return }
      fresh = true // the note tries again from the current feature branch
      continue
    }
    n.state = `merged ${sha.slice(0, 9)}`
    log(`note ${n.number}: merged ${sha.slice(0, 9)}`)
    return
  }
  n.state = 'failed'
  log(`note ${n.number}: failed after ${n.strikes} strikes`)
}

// A note whose agent returned nothing goes to the back of the queue once; a
// second time stops the run, as "How a feature with several change notes
// runs without Abdul" says.
function requeue(n, role) {
  if (!n.requeued) {
    n.requeued = true
    n.state = 'not started'
    log(`note ${n.number}: ${role} returned no result; the note runs again after the others`)
    return
  }
  n.state = 'stopped: API errors'
  halted = `${role} returned no result twice on note ${n.number}`
  log(`note ${n.number}: ${halted}; no further note starts`)
}

// ── the notes, three at once ───────────────────────────────────────────────

phase('Notes')
log(`${feature}: ${notes.filter(n => n.state === 'not started').length} note(s) to run, ${notes.filter(isMerged).length} merged already`)
await merger('report', reportBody('running'), 'report: start', 'Notes')

const running = new Map()
while (true) {
  const ready = halted ? [] : notes
    .filter(n => n.state === 'not started' && !running.has(n.number))
    .filter(n => n.waits_for.every(w => isMerged(byNumber[w] || { state: '' })))
    .sort((a, b) => (a.requeued === b.requeued ? a.number.localeCompare(b.number) : a.requeued ? 1 : -1))
  while (running.size < AT_ONCE && ready.length) {
    const n = ready.shift()
    running.set(n.number, runNote(n).then(() => n.number, err => {
      n.state = `stopped: ${String(err).slice(0, 120)}`
      return n.number
    }))
  }
  if (!running.size) break
  const done = await Promise.race([...running.values()])
  running.delete(done)
  const n = byNumber[done]
  if (!isMerged(n) && n.state !== 'not started') {
    await merger('report', reportBody('running'), `report: note ${n.number} ${n.state.split(' ')[0]}`, 'Notes')
  }
}

const merged = notes.filter(isMerged)
const failed = notes.filter(n => n.state === 'failed')
const stopped = notes.filter(n => n.state.startsWith('stopped:'))
const waiting = notes.filter(n => n.state === 'not started')
const cut = notes.filter(n => n.state.startsWith('cut'))

// ── the final check ────────────────────────────────────────────────────────

if (merged.length + cut.length === notes.length && !halted) {
  phase('Final check')
  const screensLines = notes.filter(isMerged).map(n => `${n.number}: Screens: ${n.screens}`)
  // Rounds number on from an earlier run's, so a restart's reports and lines
  // do not overwrite the earlier run's `final-1-*` files.
  let round = earlier.final.filter(l => /^Final verifier \d+:/.test(l)).length
  let fixed = false
  let tested = null
  let passed = false
  let findings = []
  let mainMoved = 0

  while (true) {
    const brought = await merger('main-in', [
      `Bring ${args.main} into the feature branch before the final check, renumbering the feature's migrations above main's first.`,
      `Answer: outcome done with commit the full sha of feature/${feature} after the merge; on a conflict you cannot resolve, abort the merge and answer outcome conflict with the \`Conflict: <files>\` line as the line and commit the sha of feature/${feature} as it stands.`,
    ].join('\n'), 'main-in', 'Final check')
    if (brought === null) { finalLines.push('main-in: merger returned no result twice'); break }
    const conflict = brought.outcome === 'conflict' ? brought.line : null
    tested = shaOf(brought) || tested
    findings = conflict ? [`main-in: ${conflict}`] : []

    while (true) {
      round += 1
      const verifyPath = `${args.reports}/final-${round}-verifier.md`
      const reviewPath = `${args.reports}/final-${round}-reviewer.md`
      const verifierLines = [
        `Feature worktree: ${args.tree} (branch feature/${feature})`,
        `Feature: ${feature}`,
        `Commit under test: ${tested}`,
        'Screens lines of every merged note:',
        ...screensLines,
        `Staging: ${args.staging || 'none; run the gate locally'}`,
        `Report path: ${verifyPath}`,
        fixed ? `Second run after the fix round: the red check's base is the commit the first run tested, ${tested}.` : '',
      ].filter(Boolean).join('\n')
      const reviewerLines = [
        `Feature worktree: ${args.tree} (branch feature/${feature})`,
        `Feature: ${feature}`,
        `Diff range: ${args.main}..feature/${feature}`,
        `Attempt: ${round}`,
        `Risk class: ${args.risk ? 'yes, a note names a class, so /code-review runs at max' : 'no'}`,
        `Report path: ${reviewPath}`,
      ].join('\n')
      const [fv, fr] = await parallel([
        () => runAgain('final-verifier', verifierLines, `final verifier ${round}`, 'Final check', FINAL_VERDICT),
        () => runAgain('final-reviewer', reviewerLines, `final reviewer ${round}`, 'Final check', FINAL_VERDICT),
      ])
      // The job reads the tree, not the verifier's message: in the rehearsal the
      // message listed the files in backticks, the old `.png$` match found none,
      // and the retaken baselines and the screens page stayed uncommitted.
      if (fv !== null) {
        await merger('baselines', [
          'Commit what the final verifier left in the feature worktree, as the job says: every changed or new file',
          `\`git -C ${args.tree} status --short\` shows under e2e/*-snapshots/ (the retaken and new baselines), plus changes/${feature}/screens.md and changes/${feature}/screens/ when they exist,`,
          'as `baselines: <screens>`. When the status shows none of these, commit nothing and say `Nothing to commit`.',
        ].join('\n'), `baselines ${round}`, 'Final check')
      }
      const vOk = fv !== null && fv.verdict === 'PASS'
      const rOk = fr !== null && fr.verdict === 'PASS'
      finalLines.push(`Final verifier ${round}: ${fv === null ? 'no result' : fv.line} (${verifyPath})`)
      finalLines.push(`Final reviewer ${round}: ${fr === null ? 'no result' : fr.line} (${reviewPath})`)
      if (vOk && rOk && !findings.length) { passed = true; break }
      if (!vOk) strikesByRole['final-verifier'] += 1
      if (!rOk) strikesByRole['final-reviewer'] += 1
      if (fixed) break
      fixed = true
      const fixPrompt = [
        `Tree: ${args.tree} (branch feature/${feature})`,
        `Feature: ${feature}`,
        'Final fix round: there is no note; the findings below are the work. Commit on the feature branch as `fix: <what>`.',
        `Base commit (the commit the final check tested; each new test must fail there): ${tested}`,
        'Attempt: 1 of 1',
        `Findings: ${[...findings, fv === null ? '' : 'final verifier: ' + fv.line, fr === null ? '' : 'final reviewer: ' + fr.line].filter(Boolean).join('; ')}; the two reports below hold each finding in full.`,
        `Final verifier report: ${fv === null ? 'none' : verifyPath}`,
        `Final reviewer report: ${fr === null ? 'none' : reviewPath}`,
      ].join('\n')
      const fix = await runAgain('implementer', fixPrompt, 'fix round: implementer', 'Final check', BUILT)
      if (fix === null) { finalLines.push('Fix round: implementer returned no result twice'); break }
      finalLines.push(`Fix round: ${fix.line}`)
      findings = []
    }
    if (!passed) break

    // The final report goes on the feature branch first, so the merge commit
    // carries it and main-out adds only the `Merged:` line on main.
    phase('Merge')
    await merger('report', reportBody('merged', finalParts()), 'report: merged, before main-out', 'Merge')
    const out = await merger('main-out', [
      'The final check passed. Merge the feature into local main as the job says: fast-forward only, as a merge commit, through the hooks.',
      `The report on the feature branch already reads State: merged with the final check and the screens; on success add only the \`Merged:\` line to the copy on ${args.main} and commit it there.`,
      `Answer: outcome done with commit the full sha of the merge commit on ${args.main}; on a \`REFUSED:\` line from the hooks outcome refused with that line; when main moved since the final check, outcome main moved and nothing merged.`,
    ].join('\n'), 'main-out', 'Merge')
    if (out === null) { finalLines.push('main-out: merger returned no result twice'); break }
    mergeCommit = out.outcome === 'done' ? shaOf(out) : null
    if (mergeCommit) { finalState = 'merged'; break }
    if (out.outcome === 'main moved' && mainMoved < 2) {
      mainMoved += 1
      log('main moved since the final check; it runs again')
      passed = false
      fixed = true // no second fix round
      continue
    }
    finalLines.push(`main-out: ${out.line}`)
    break
  }
}

// ── the report and the result ──────────────────────────────────────────────

// A merged feature's report was written before main-out and the merge
// carried it; any other end writes the report as stopped, a refused or
// skipped main-out included.
if (finalState !== 'merged') {
  await merger('report', reportBody('stopped', finalParts()), 'report: stopped', 'Notes')
}

const toDecide = notes.reduce((k, n) => k + n.decide.length, 0)
const parts = [`${merged.length} of ${notes.length} notes merged`]
if (failed.length) parts.push(`${failed.length} failed`)
if (stopped.length) parts.push(`${stopped.length} stopped`)
if (waiting.length) parts.push(`${waiting.length} not started`)
if (toDecide) parts.push(`${toDecide} to decide`)
const notice = finalState === 'merged'
  ? `${feature}: merged into ${args.main} at ${String(mergeCommit).slice(0, 9)}, ${merged.length} note(s)${toDecide ? `, ${toDecide} to decide` : ''}`
  : `${feature}: ${parts.join(', ')}${halted ? `; stopped: ${halted}` : ''}`

return {
  feature,
  state: finalState,
  mergeCommit,
  halted,
  notes: notes.map(n => ({ number: n.number, state: n.state, strikes: n.strikes, attempts: n.attempts, last_report: n.last_report || null })),
  strikesByRole,
  finalLines,
  notice,
}
