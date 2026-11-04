// Drives the static and form checks on a fixture site: every refusal they must make, and one control that passes.
//   node --test site-checks/scripts/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import * as staticChecks from './static.mjs';
import * as form from './form.mjs';
import * as browser from './browser.mjs';

const HOME = '<!doctype html><html><head><title>Home</title><meta name="description" content="Home page"><meta name="robots" content="noindex">'
  + '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"X"}</script>'
  + '<script type="module" src="/_astro/home.js"></script></head>'
  + '<body><main><h1 id="top">Hello</h1><p>Some real text here.</p><a href="/about">About</a> <a href="/about#team">Team</a> <a href="https://x.test">Out</a></main></body></html>';
const ABOUT = '<!doctype html><html><head><title>About</title><meta name="description" content="About page"><meta name="robots" content="noindex">'
  + '<script type="application/ld+json">{"@type":"AboutPage"}</script></head>'
  + '<body><main><h2 id="team">Team</h2><p>People.</p><a href="/">Home</a></main></body></html>';

function fixture(overrides = {}) {
  const dist = mkdtempSync(join(tmpdir(), 'site-checks-'));
  const files = {
    'index.html': HOME,
    'about/index.html': ABOUT,
    '_astro/home.js': 'import "./shared.js"; console.log(1);',
    '_astro/shared.js': 'export const a = 1;',
    'sitemap.xml': '<urlset><url><loc>https://x.test/</loc></url><url><loc>https://x.test/about</loc></url></urlset>',
    'llms.txt': '# X\n- [Home](https://x.test/)\n- [About](https://x.test/about)\n',
    'robots.txt': 'User-agent: *\nDisallow: /\n',
    ...overrides,
  };
  for (const [name, text] of Object.entries(files)) {
    if (text === null) continue;
    mkdirSync(dirname(join(dist, name)), { recursive: true });
    writeFileSync(join(dist, name), text);
  }
  return dist;
}

const refusals = (overrides, opts = {}) => {
  const dist = fixture(overrides);
  try { return staticChecks.runAll(dist, { ...staticChecks.DEFAULTS, ...opts }); } finally { rmSync(dist, { recursive: true }); }
};
const expectOne = (refused, word) => assert.ok(refused.some((r) => r.includes(word)), `expected a refusal naming "${word}", got: ${JSON.stringify(refused)}`);

test('the clean fixture passes as an mvp build', () => assert.deepEqual(refusals({}), []));

test('an empty build is refused rather than passed', () => {
  const dist = mkdtempSync(join(tmpdir(), 'site-checks-empty-'));
  try { expectOne(staticChecks.runAll(dist, staticChecks.DEFAULTS), 'nothing was measured'); } finally { rmSync(dist, { recursive: true }); }
});

test('a link to a page outside the build is refused', () => expectOne(refusals({ 'about/index.html': ABOUT.replace('href="/"', 'href="/missing"') }), 'reaches no page'));
test('a link to an anchor that no page carries is refused', () => expectOne(refusals({ 'index.html': HOME.replace('#team', '#board') }), '#board'));
test('a relative link the checker cannot place is refused', () => expectOne(refusals({ 'index.html': HOME.replace('href="/about"', 'href="about"') }), 'cannot place'));

test('a page over the first-load size is refused', () => expectOne(refusals({ '_astro/shared.js': 'x'.repeat(2000).split('').map((c, i) => `const v${i}=${i};`).join('\n') }, { firstKb: 1 }), 'at first load'));
test('a dynamic import counts only against the late total', () => {
  const late = refusals({ '_astro/home.js': 'import("./big.js");', '_astro/big.js': Array.from({ length: 3000 }, (_, i) => `export const v${i}=${i};`).join('\n') }, { firstKb: 1, lateKb: 2 });
  expectOne(late, 'with late loads');
  assert.ok(!late.some((r) => r.includes('at first load')), late.join('\n'));
});
test('a dynamic import with a computed path is refused', () => expectOne(refusals({ '_astro/home.js': 'const p = "./a.js"; import(p);' }), 'computed path'));

test('two pages sharing a title are refused', () => expectOne(refusals({ 'about/index.html': ABOUT.replace('<title>About</title>', '<title>Home</title>') }), 'title "Home" is also'));
test('a page with no meta description is refused', () => expectOne(refusals({ 'about/index.html': ABOUT.replace(/<meta name="description"[^>]*>/, '') }), 'no meta description'));
test('a page whose main holds no text without JavaScript is refused', () => expectOne(refusals({ 'about/index.html': ABOUT.replace(/<main>[\s\S]*<\/main>/, '<main><div id="team" data-app></div></main>') }), 'no text without JavaScript'));

test('a page with no JSON-LD is refused', () => expectOne(refusals({ 'about/index.html': ABOUT.replace(/<script type="application\/ld\+json">[^<]*<\/script>/, '') }), 'no JSON-LD block'));
test('JSON-LD that does not parse is refused', () => expectOne(refusals({ 'about/index.html': ABOUT.replace('{"@type":"AboutPage"}', '{"@type":') }), 'does not parse'));
test('JSON-LD with no @type is refused', () => expectOne(refusals({ 'about/index.html': ABOUT.replace('{"@type":"AboutPage"}', '{"name":"x"}') }), 'no @type'));

test('a page missing from the sitemap is refused', () => expectOne(refusals({ 'sitemap.xml': '<urlset><url><loc>https://x.test/</loc></url></urlset>' }), 'does not list /about'));
test('a sitemap entry outside the build is refused', () => expectOne(refusals({ 'sitemap.xml': '<urlset><url><loc>https://x.test/</loc></url><url><loc>https://x.test/about</loc></url><url><loc>https://x.test/gone</loc></url></urlset>' }), 'lists /gone'));
test('a page missing from llms.txt is refused', () => expectOne(refusals({ 'llms.txt': '- [Home](https://x.test/)\n' }), 'llms.txt: does not list /about'));
test('a missing llms.txt is refused', () => expectOne(refusals({ 'llms.txt': null }), 'llms.txt: missing'));

test('an mvp page without noindex is refused', () => expectOne(refusals({ 'about/index.html': ABOUT.replace('<meta name="robots" content="noindex">', '') }), 'sends noindex, this page does not'));
test('an mvp robots.txt that lets crawlers in is refused', () => expectOne(refusals({ 'robots.txt': 'User-agent: *\nAllow: /\n' }), 'disallows / for every crawler'));
test('a production build still sending noindex is refused', () => expectOne(refusals({}, { env: 'production' }), 'never sends noindex'));
test('a production robots.txt that keeps an AI crawler out is refused', () => {
  const noindexOff = { 'index.html': HOME.replace('<meta name="robots" content="noindex">', ''), 'about/index.html': ABOUT.replace('<meta name="robots" content="noindex">', '') };
  expectOne(refusals({ ...noindexOff, 'robots.txt': 'User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /\n' }, { env: 'production' }), 'keeps GPTBot out');
  assert.deepEqual(refusals({ ...noindexOff, 'robots.txt': 'User-agent: *\nAllow: /\n' }, { env: 'production' }), []);
});
test('a robots.txt line the checker cannot place is refused', () => expectOne(refusals({ 'robots.txt': 'User-agent: *\nDisallow: /\nsomething odd\n' }), 'cannot place "something odd"'));

test('the static flags are read and a bad one is refused', () => {
  assert.deepEqual(staticChecks.parseArgs(['out', '--env', 'production', '--first-kb', '120']), { env: 'production', firstKb: 120, lateKb: 150, dist: 'out' });
  assert.throws(() => staticChecks.parseArgs(['--env', 'live']), /mvp or production/);
  assert.throws(() => staticChecks.parseArgs(['--first-kb', 'ten']), /positive number/);
  assert.throws(() => staticChecks.parseArgs(['--size']), /unknown flag/);
});

test('the form check passes only when five honeypot posts are refused and the sixth is rate limited', async () => {
  const opts = form.parseArgs(['--url', 'http://x.test/api', '--honeypot', 'website', '--field', 'name=Bot']);
  const seen = [];
  const fake = (statuses) => async (url, fields) => { seen.push(fields); return statuses.shift(); };
  assert.deepEqual((await form.run(opts, fake([400, 400, 400, 400, 400, 429]))).refused, []);
  assert.equal(seen[0].website, 'https://bot.example');
  assert.equal(seen[0].name, 'Bot');
  expectOne((await form.run(opts, fake([200, 400, 400, 400, 400, 429]))).refused, 'instead of a 4xx refusal');
  expectOne((await form.run(opts, fake([400, 400, 400, 400, 400, 400]))).refused, 'instead of 429');
  expectOne((await form.run(opts, fake([400, 429, 400, 400, 400, 429]))).refused, 'before the limit');
  expectOne((await form.run(opts, fake([500, 400, 400, 400, 400, 429]))).refused, 'status 500');
});

test('the form flags are read and a bad one is refused', () => {
  assert.equal(form.parseArgs(['--url', 'u', '--limit', '3']).limit, 3);
  assert.throws(() => form.parseArgs(['--limit', '3']), /--url is required/);
  assert.throws(() => form.parseArgs(['--url', 'u', '--limit', '0']), /positive whole/);
  assert.throws(() => form.parseArgs(['--url', 'u', '--field', 'name']), /name=value/);
});

test('the browser judge applies the thresholds to a Lighthouse result', () => {
  const lhr = (perf, lcp, cls) => ({
    categories: { performance: { score: perf }, accessibility: { score: 1 }, 'best-practices': { score: 1 }, seo: { score: 1 } },
    audits: { 'largest-contentful-paint': { numericValue: lcp }, 'cumulative-layout-shift': { numericValue: cls } },
  });
  assert.deepEqual(browser.judge(lhr(0.97, 1500, 0.01), browser.DEFAULTS).misses, []);
  assert.deepEqual(browser.judge(lhr(0.9, 2500, 0.1), browser.DEFAULTS).misses, ['Performance 90', 'LCP 2.50 s', 'CLS 0.100']);
  assert.deepEqual(browser.judge(lhr(0.9, 1000, 0.01), { ...browser.DEFAULTS, perf: 90 }).misses, []);
  assert.throws(() => browser.parseArgs([]), /--url is required/);
  assert.deepEqual(browser.parseArgs(['--url', 'u', '--widths', '320,1440']).widths, [320, 1440]);
});
