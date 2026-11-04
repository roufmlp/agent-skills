// The shared browser checks for a site, run against the built site served at --url. Refuses when any page fails one.
// Run from the product's folder: Lighthouse, Playwright and axe load from its own node_modules.
//
//   node browser.mjs --url http://localhost:4321 [dist] [--env mvp|production] [--perf 95] [--lcp 2.0] [--cls 0.05]
//                    [--widths 320,768,1440] [--channel chrome]
//
// Checks, with their defaults (a brief changes a number in one line, which becomes a flag here):
//   lighthouse  mobile and desktop, every page: Performance 95 or more; Accessibility, Best Practices and SEO 100;
//               LCP under 2.0 s; CLS under 0.05. An mvp build sends noindex on purpose, so is-crawlable is skipped.
//   axe         no violation on any page at any of the widths
//   scroll      no page scrolls sideways at any of the widths
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { readBuild } from './static.mjs';

export const DEFAULTS = { env: 'mvp', perf: 95, lcp: 2.0, cls: 0.05, widths: [320, 768, 1440], channel: 'chrome', dist: 'dist' };

export function parseArgs(argv) {
  const opts = { ...DEFAULTS, url: undefined };
  const rest = [...argv];
  while (rest.length) {
    const a = rest.shift();
    if (a === '--url') opts.url = rest.shift();
    else if (a === '--env') opts.env = rest.shift();
    else if (a === '--perf') opts.perf = Number(rest.shift());
    else if (a === '--lcp') opts.lcp = Number(rest.shift());
    else if (a === '--cls') opts.cls = Number(rest.shift());
    else if (a === '--widths') opts.widths = rest.shift().split(',').map(Number);
    else if (a === '--channel') opts.channel = rest.shift();
    else if (a.startsWith('--')) throw new Error(`unknown flag ${a}`);
    else opts.dist = a;
  }
  if (!opts.url) throw new Error('--url is required: the address the built site is served at');
  if (!['mvp', 'production'].includes(opts.env)) throw new Error(`--env must be mvp or production, not ${opts.env}`);
  for (const k of ['perf', 'lcp', 'cls']) if (!Number.isFinite(opts[k]) || opts[k] <= 0) throw new Error(`--${k} must be a positive number`);
  if (!opts.widths.length || opts.widths.some((w) => !Number.isInteger(w) || w <= 0)) throw new Error('--widths must be positive whole numbers, comma separated');
  return opts;
}

// Lighthouse scores and the two timings for one page in one form, against the thresholds.
export function judge(lhr, { perf, lcp, cls }) {
  const score = (k) => Math.round((lhr.categories[k]?.score ?? 0) * 100);
  const s = { perf: score('performance'), a11y: score('accessibility'), bp: score('best-practices'), seo: score('seo') };
  const lcpMs = lhr.audits['largest-contentful-paint'].numericValue;
  const clsValue = lhr.audits['cumulative-layout-shift'].numericValue;
  const misses = [];
  if (s.perf < perf) misses.push(`Performance ${s.perf}`);
  for (const [k, name] of [['a11y', 'Accessibility'], ['bp', 'Best Practices'], ['seo', 'SEO']]) if (s[k] < 100) misses.push(`${name} ${s[k]}`);
  if (lcpMs >= lcp * 1000) misses.push(`LCP ${(lcpMs / 1000).toFixed(2)} s`);
  if (clsValue >= cls) misses.push(`CLS ${clsValue.toFixed(3)}`);
  const line = `perf ${s.perf}  a11y ${s.a11y}  bp ${s.bp}  seo ${s.seo}  LCP ${(lcpMs / 1000).toFixed(2)} s  CLS ${clsValue.toFixed(3)}`;
  return { misses, line };
}

// The product's own copies of the three packages, so one version runs the checks and the tests.
function load(name) {
  const req = createRequire(join(process.cwd(), 'package.json'));
  let path;
  try { path = req.resolve(name); } catch { throw new Error(`${name} is not installed in ${process.cwd()}; add it as a devDependency`); }
  return import(pathToFileURL(path).href);
}

export async function run(opts) {
  const pages = [...readBuild(opts.dist).pages.keys()].sort();
  if (pages.length === 0) return [`${opts.dist}: no pages found, so nothing was measured`];
  const [{ default: lighthouse }, { default: desktop }, playwright, axe] = await Promise.all([
    load('lighthouse'), load('lighthouse/core/config/desktop-config.js'), load('@playwright/test'), load('@axe-core/playwright'),
  ]);
  // The last two are CommonJS, so their exports sit on `default` when imported this way.
  const chromium = playwright.chromium ?? playwright.default.chromium;
  const AxeBuilder = axe.default?.AxeBuilder ?? axe.AxeBuilder ?? axe.default?.default ?? axe.default;
  const refused = [];
  const debug = 9339;
  const browser = await chromium.launch({ channel: opts.channel, args: [`--remote-debugging-port=${debug}`] });
  try {
    const settings = opts.env === 'mvp' ? { skipAudits: ['is-crawlable'] } : {};
    const forms = [
      ['mobile', { extends: 'lighthouse:default', settings }],
      ['desktop', { ...desktop, settings: { ...desktop.settings, ...settings } }],
    ];
    for (const path of pages) for (const [form, config] of forms) {
      const result = await lighthouse(`${opts.url}${path}`, { port: debug, logLevel: 'error', onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'] }, config);
      const lhr = result?.lhr;
      if (!lhr || lhr.runtimeError) { refused.push(`lighthouse ${path} ${form}: no result (${lhr?.runtimeError?.message ?? 'no report'})`); continue; }
      const { misses, line } = judge(lhr, opts);
      console.log(`${path.padEnd(22)} ${form.padEnd(8)} ${line}`);
      if (misses.length) {
        const failed = Object.values(lhr.audits).filter((a) => a.score !== null && a.score < 1 && a.scoreDisplayMode === 'binary').map((a) => a.id);
        refused.push(`lighthouse ${path} ${form}: ${misses.join(', ')}${failed.length ? ` (failed audits: ${failed.join(', ')})` : ''}`);
      }
    }
    for (const width of opts.widths) {
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      const page = await context.newPage();
      for (const path of pages) {
        await page.goto(`${opts.url}${path}`);
        // axe reads colours as painted, so a piece still fading in reads as low contrast. Let entrances finish first.
        await page.evaluate(() => Promise.all(document.getAnimations()
          .filter((a) => a.playState === 'running' && Number.isFinite(a.effect?.getComputedTiming().endTime))
          .map((a) => a.finished.catch(() => null))));
        const { violations } = await new AxeBuilder({ page }).analyze();
        for (const v of violations) refused.push(`axe ${path} at ${width}px: ${v.id} on ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        if (overflow !== 0) refused.push(`scroll ${path} at ${width}px: scrolls sideways by ${overflow}px`);
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }
  return refused;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const opts = parseArgs(process.argv.slice(2));
  const refused = await run(opts);
  if (refused.length) {
    console.error(`\nBrowser checks refused ${refused.length}:\n` + refused.map((r) => `  ${r}`).join('\n'));
    process.exit(1);
  }
  console.log(`\nBrowser checks passed: every page, mobile and desktop, at ${opts.widths.join(', ')}px.`);
}
