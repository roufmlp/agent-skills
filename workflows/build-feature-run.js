export const meta = {
  name: 'build-feature-run',
  description: 'Build an approved feature plan: each change note through its own implementer, verifier and reviewer, three notes at once, one merger between them, then the final check and the merge into local main',
  phases: [
    { title: 'Notes', detail: 'one implementer, verifier and reviewer per note, three notes at once' },
    { title: 'Final check', detail: 'the whole feature: final verifier and final reviewer, three fix rounds' },
    { title: 'Merge', detail: 'fast-forward only, as a --no-ff merge commit, through the hooks; held while a ruling waits for the human' },
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
//
// Nobody answers a question mid-run, and the script rules on nothing. A note
// that needs an answer stops with its class, its question and its default in
// the role's typed answer; the result carries them as `stops`, and the session
// rules between runs (`lib/rulings.py`). A ruling the human did not make
// himself holds the merge into local main until he confirms it: `args.gate_open`.

const SKILLS = '~/.claude/skills/workflow'
const AT_ONCE = 3
const MAX_STRIKES = 3
const FIX_ROUNDS = 3 // the fix rounds one final check gets before the run stops

const feature = args.feature
const notes = args.notes.map(n => ({ ...n, requeued: false, checked: false, stop: null, reports: [], decide: [], defaults: [], edits: [] }))
const byNumber = Object.fromEntries(notes.map(n => [n.number, n]))
const strikesByRole = { implementer: 0, verifier: 0, reviewer: 0, 'note-checker': 0, merger: 0, 'final-verifier': 0, 'final-reviewer': 0, ...((args.earlier || {}).strikes || {}) }
let halted = null // the reason no further note starts
let finalState = 'stopped'
// An earlier run's lines in the three report parts a restart keeps; the
// session's feature_run.py read them from the report.
const earlier = { defaults: [], edits: [], final: [], tooling: [], ...(args.earlier || {}) }
let finalLines = [...earlier.final] // the `## Final check` lines, one per final role run
let mergeCommit = null
const gateOpen = args.gate_open || [] // notes whose ruling by default or panel has no answer yet
const away = args.away || [] // the report's "Ruled while you were away" lines, from the plan
const toolingStops = [...earlier.tooling] // one line per tool fault, kept across restarts
const stops = [] // every stop of this run, typed, for the session
const fixNotes = [] // final-check findings that need a new test, so a fix note

// ── helpers ────────────────────────────────────────────────────────────────

// Every role answers in a typed form, not in prose: `agent()` with a schema
// makes the runtime ask the role for these fields and refuse an answer that
// does not fit, before this script sees it. In the rehearsal the script read
// the verdict word out of the message text, found PASS in a reject's third
// line ("All 4 tests pass now"), and merged a rejected note. The long report
// still goes to the file the prompt names; the form carries the decision.
const LINES = { type: 'array', items: { type: 'string' } }
// A stop is typed too, so no script and no session reads a class, a question
// or a default out of prose. `question`: the work needs an answer of the
// human's kind. `tooling`: a hook, a check script or the desktop app refused a
// step and the role had no other road; that is a fault of the tools, never a
// question about the feature, and never a strike.
const RISK_CLASSES = ['money', 'access', 'migration', 'data leaving']
const STOP = {
  type: 'object',
  description: 'kind none unless you stop; the other fields are then empty strings and class none',
  properties: {
    kind: { enum: ['none', 'question', 'tooling'], description: 'question: the work needs an answer of the human\'s kind. tooling: a hook, a check script or the app refused a step you could not do another way' },
    class: { enum: ['none', ...RISK_CLASSES], description: 'question only: money; access (authentication, a right, a role, a row policy); migration (a migration\'s direction); data leaving (data leaving the product, or a public contract); none for any other question' },
    question: { type: 'string', description: 'question: the question in plain words, one line, no file path in it. tooling: the refusal line exactly as the tool printed it' },
    default: { type: 'string', description: 'question only: the road you would take, one line, written so the note can be changed from it without you' },
    tool: { enum: ['', 'hook', 'check script', 'desktop app', 'other'], description: 'tooling only: the family of the tool that refused' },
  },
  required: ['kind', 'class', 'question', 'default', 'tool'],
}
const VERDICT = {
  type: 'object',
  properties: {
    verdict: { enum: ['PASS', 'REJECT'], description: 'REJECT when any step or ground failed' },
    line: { type: 'string', description: 'one line: the verdict and the first ground, or "all steps passed"' },
    stop: { ...STOP, description: 'kind none, or kind tooling when a tool refused a step of yours; a verdict role asks no question' },
  },
  required: ['verdict', 'line', 'stop'],
}
const FINAL_VERDICT = {
  type: 'object',
  properties: {
    verdict: { enum: ['PASS', 'FINDINGS'] },
    line: { type: 'string', description: 'one line: the verdict and the steps or findings that failed, or "all steps passed"' },
    stop: { ...STOP, description: 'kind none, or kind tooling when a tool refused a step of yours; a verdict role asks no question' },
  },
  required: ['verdict', 'line', 'stop'],
}
const BUILT = {
  type: 'object',
  properties: {
    line: { type: 'string', description: 'one line: what was built and the commit' },
    edits: { ...LINES, description: 'Done-check edits: one line per done-check file edited, with what changed; empty when none' },
    defaults: { ...LINES, description: 'Defaults taken: one line each; empty when none' },
    keeps: { ...LINES, description: 'the keeps: test titles; empty when none' },
    needs_note: { ...LINES, description: 'final fix round only: one line per finding that needs a new test file, so a fix note; empty otherwise' },
    stop: STOP,
  },
  required: ['line', 'edits', 'defaults', 'keeps', 'needs_note', 'stop'],
}
const CHECKED = {
  type: 'object',
  properties: {
    outcome: { enum: ['corrected', 'sound', 'stopped'] },
    line: { type: 'string', description: 'the first line of the report: "Corrected: ...", "Sound: ..." or "Stopped: ..."' },
    stop: { ...STOP, description: 'kind question with its class, question and default when outcome is stopped; kind tooling when a tool refused your edit or your report; else kind none' },
  },
  required: ['outcome', 'line', 'stop'],
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

// A verdict role's tooling stop, or null. It asks no question.
function toolingOf(out) {
  const stop = stopOf(out)
  return stop !== null && stop.kind === 'tooling' ? stop : null
}

// The sha a merger job answered with, when it is one.
function shaOf(out) {
  const sha = String((out && out.commit) || '').trim()
  return SHA.test(sha) ? sha : null
}

// One line that fits a table cell.
function oneLine(text) {
  return String(text || '').replace(/[\r\n|]+/g, ' ').replace(/\s+/g, ' ').trim()
}

// The typed stop of a role's answer, or null when the role did not stop.
function stopOf(out) {
  const stop = (out && out.stop) || {}
  if (stop.kind === 'tooling') return { kind: 'tooling', tool: stop.tool || 'other', line: oneLine(stop.question) }
  if (stop.kind === 'question') {
    return { kind: 'question', class: stop.class || 'none', question: oneLine(stop.question), default: oneLine(stop.default) }
  }
  return null
}

// Record a stop under its number (a note's, or `final`) and return the report state.
function recordStop(number, role, stop) {
  stops.push({ number, role, ...stop })
  if (stop.kind === 'tooling') {
    toolingStops.push(`${String(args.started).slice(0, 10)} ${number}: ${stop.tool}: ${stop.line}`)
    return `stopped: tooling: ${stop.tool}: ${stop.line}`
  }
  return `stopped: ${stop.question}`
}

// A note stops: its row says why, and a question goes under Decide with its
// class and its default. A tooling stop has no Decide line.
function stopNote(n, role, stop) {
  n.state = recordStop(n.number, role, stop)
  n.stop = stop
  if (stop.kind === 'question') n.decide.push(`[${stop.class}] ${stop.question} Default: ${stop.default}`)
  log(`note ${n.number}: ${n.state}`)
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
    'Decide, one line per question a note stopped on, with its class in brackets and its default:',
    ...linesOrNone(notes.flatMap(n => n.decide.map(l => `${n.number}: ${l}`))),
    '',
    'Tooling stops, one line per tool fault, as given (an earlier run\'s lines first):',
    ...linesOrNone(toolingStops),
    '',
    'Ruled while you were away, one line per ruling by default or panel, as given; write "none" when there is none:',
    ...linesOrNone(away),
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
    `3. Give the tree what it needs to run: \`cp -c -R ${args.repo}/node_modules ${n.worktree}/node_modules\` (an APFS clone; plain \`cp -R\` if -c fails), \`cp ${args.repo}/.env.local ${n.worktree}/.env.local\` when that file exists, then claim a database the way the product's .claude/run-isolation.json says, in the worktree: \`node scripts/run-db.mjs claim --batch ${args.batch} --slot note_${n.number} --tree ${n.worktree}\`, so each note's tree has a database of its own. Skip a step whose file or script the product does not have, and say so.`,
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

// A strike: record the report, and at the second strike spawn the note
// checker. Returns false when the note stopped, true when it tries again.
async function strike(n, role, reportPath) {
  n.strikes += 1
  strikesByRole[role] += 1
  n.last_report = reportPath
  if (!n.reports.includes(reportPath)) n.reports.push(reportPath)
  log(`note ${n.number}: strike ${n.strikes} (${role})`)
  if (n.strikes !== 2 || n.checked) return true
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
  if (out === null) { n.state = 'stopped: note-checker returned no result'; return false }
  n.reports.push(checkPath)
  const stop = stopOf(out)
  if (stop !== null && (stop.kind === 'tooling' || out.outcome === 'stopped')) { stopNote(n, 'note-checker', stop); return false }
  if (out.outcome === 'stopped') {
    // Stopped with no typed stop: a class nobody named is never read as
    // outside the risk classes, so this one waits for the human.
    stopNote(n, 'note-checker', { kind: 'question', class: 'unclassified', question: oneLine(out.line), default: '' })
    return false
  }
  if (out.outcome === 'corrected') { n.defaults.push(out.line); log(`note ${n.number}: ${out.line}`) }
  return true
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
    const builtStop = stopOf(built)
    if (builtStop !== null) { stopNote(n, 'implementer', builtStop); return }

    const verifyPath = `${args.reports}/${tag}-verifier.md`
    const verified = await run('verifier', gatePrompt(n, base, verifyPath), `note ${n.number}: verifier ${n.attempts}`, 'Notes', VERDICT)
    if (verified === null) { n.attempts -= 1; return requeue(n, 'verifier') }
    if (toolingOf(verified) !== null) { stopNote(n, 'verifier', toolingOf(verified)); return }
    if (verified.verdict !== 'PASS') {
      if (!(await strike(n, 'verifier', verifyPath))) return
      continue
    }

    const reviewPath = `${args.reports}/${tag}-reviewer.md`
    const keeps = built.keeps
    const reviewed = await run('reviewer', gatePrompt(n, base, reviewPath, [
      `Done-check edits from the implementer: ${n.edits.length ? n.edits.join('; ') : 'none'}`,
      `keeps: titles: ${keeps.length ? keeps.join('; ') : 'none'}`,
    ]), `note ${n.number}: reviewer ${n.attempts}`, 'Notes', VERDICT)
    if (reviewed === null) { n.attempts -= 1; return requeue(n, 'reviewer') }
    if (toolingOf(reviewed) !== null) { stopNote(n, 'reviewer', toolingOf(reviewed)); return }
    if (reviewed.verdict !== 'PASS') {
      if (!(await strike(n, 'reviewer', reviewPath))) return
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
      if (!(await strike(n, 'merger', mergePath))) return
      fresh = true // the note tries again from the current feature branch
      continue
    }
    n.state = `merged ${sha.slice(0, 9)}`
    log(`note ${n.number}: merged ${sha.slice(0, 9)}`)
    return
  }
  // A note gets one automatic re-arm, which the session writes as a ruling
  // between runs. Its second failure waits for the human with no timeout,
  // and the other notes run on.
  n.state = n.rearmed ? 'waiting: failed again after its re-arm' : 'failed'
  log(`note ${n.number}: ${n.state} after ${n.strikes} strikes`)
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
  let fixes = 0
  let tested = null
  let passed = false
  let findings = []
  let mainMoved = 0
  // An earlier run's final check passed and was held at the gate, and nothing
  // but the plan and the report changed since (feature_run.py, `held`): this
  // run goes straight to the merge. Main-out still refuses when main moved.
  let standing = Boolean(args.held)

  while (true) {
    if (standing) {
      standing = false
      passed = true
      log('the final check of the held run stands; nothing but the plan and the report changed since')
    } else {
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
          fixes ? `Run after fix round ${fixes}: the red check's base is the commit the first run tested, ${tested}.` : '',
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
        // A tool that refused a final role is not a finding: no fix round can
        // clear it, so none is spent on it.
        const faults = [['final-verifier', toolingOf(fv)], ['final-reviewer', toolingOf(fr)]].filter(f => f[1] !== null)
        if (faults.length) {
          for (const [role, stop] of faults) finalLines.push(`Final check ${recordStop('final', role, stop)}`)
          break
        }
        if (vOk && rOk && !findings.length) { passed = true; break }
        if (!vOk) strikesByRole['final-verifier'] += 1
        if (!rOk) strikesByRole['final-reviewer'] += 1
        if (fixes >= FIX_ROUNDS) break
        fixes += 1
        // Every finding of the round goes to the one fix round, in one batch.
        const fixPrompt = [
          `Tree: ${args.tree} (branch feature/${feature})`,
          `Feature: ${feature}`,
          'Final fix round: there is no note; the findings below are the work. Commit on the feature branch as `fix: <what>`.',
          `Base commit (the commit the final check tested; each new test must fail there): ${tested}`,
          `Attempt: ${fixes} of ${FIX_ROUNDS}`,
          `Findings, all of them in one batch: ${[...findings, fv === null ? '' : 'final verifier: ' + fv.line, fr === null ? '' : 'final reviewer: ' + fr.line].filter(Boolean).join('; ')}; the two reports below hold each finding in full.`,
          `Final verifier report: ${fv === null ? 'none' : verifyPath}`,
          `Final reviewer report: ${fr === null ? 'none' : reviewPath}`,
        ].join('\n')
        const fix = await runAgain('implementer', fixPrompt, `fix round ${fixes}: implementer`, 'Final check', BUILT)
        if (fix === null) { finalLines.push(`Fix round ${fixes}: implementer returned no result twice`); break }
        finalLines.push(`Fix round ${fixes}: ${fix.line}`)
        const fixStop = stopOf(fix)
        if (fixStop !== null) { finalLines.push(`Fix round ${fixes} ${recordStop('final', 'implementer', fixStop)}`); break }
        // A finding that needs a new test is a fix note, which the session
        // writes under a ruling; no further round can pass without it.
        if (fix.needs_note.length) {
          for (const line of fix.needs_note) { fixNotes.push(oneLine(line)); finalLines.push(`Fix note needed: ${oneLine(line)}`) }
          break
        }
        findings = []
      }
    }
    if (!passed) break

    // The one gate before local main: a ruling by default or panel that the
    // human has not confirmed holds the merge. The hook refuses it too.
    if (gateOpen.length) {
      finalState = 'held'
      log(`held before ${args.main}: the rulings on ${gateOpen.join(', ')} wait for the human`)
      break
    }

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
      fixes = FIX_ROUNDS // no further fix round
      continue
    }
    finalLines.push(`main-out: ${out.line}`)
    break
  }
}

// ── the report and the result ──────────────────────────────────────────────

// A merged feature's report was written before main-out and the merge
// carried it; a held feature's report says so; any other end writes the
// report as stopped, a refused or skipped main-out included.
if (finalState === 'held') {
  await merger('report', reportBody('held', finalParts()), 'report: held', 'Final check')
} else if (finalState !== 'merged') {
  await merger('report', reportBody('stopped', finalParts()), 'report: stopped', 'Notes')
}

const waitingForHuman = notes.filter(n => n.state.startsWith('waiting:'))
const toDecide = stops.filter(s => s.kind === 'question').length
const toolFaults = stops.filter(s => s.kind === 'tooling').length
const parts = [`${merged.length} of ${notes.length} notes merged`]
if (failed.length) parts.push(`${failed.length} failed`)
if (stopped.length) parts.push(`${stopped.length} stopped`)
if (waitingForHuman.length) parts.push(`${waitingForHuman.length} waiting for you`)
if (waiting.length) parts.push(`${waiting.length} not started`)
if (toDecide) parts.push(`${toDecide} to decide`)
if (toolFaults) parts.push(`${toolFaults} tool fault(s)`)
if (fixNotes.length) parts.push(`${fixNotes.length} fix note(s) needed`)
const notice = finalState === 'merged'
  ? `${feature}: merged into ${args.main} at ${String(mergeCommit).slice(0, 9)}, ${merged.length} note(s)`
  : finalState === 'held'
    ? `${feature}: the final check passed; ${gateOpen.length} ruling(s) to confirm before the merge into ${args.main}`
    : `${feature}: ${parts.join(', ')}${halted ? `; stopped: ${halted}` : ''}`

return {
  feature,
  state: finalState,
  mergeCommit,
  halted,
  notes: notes.map(n => ({ number: n.number, state: n.state, strikes: n.strikes, attempts: n.attempts, last_report: n.last_report || null })),
  // What the session rules on between runs: each stop with its typed parts,
  // the findings that need a fix note, and how long to wait for the human.
  stops,
  fix_notes: fixNotes,
  gate_open: gateOpen,
  ruling_wait_seconds: args.ruling_wait_seconds,
  strikesByRole,
  finalLines,
  notice,
}
