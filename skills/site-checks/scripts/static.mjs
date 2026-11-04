// The shared static checks for a site, run over its built output. Refuses the build when any page fails one.
// Reads every page in the build and refuses what it cannot place, so nothing passes unmeasured.
//
//   node static.mjs [dist] [--env mvp|production] [--first-kb 100] [--late-kb 150]
//
// Checks, with their defaults (a brief changes a number in one line, which becomes a flag here):
//   links      every internal <a href> reaches a page in the build, and its #anchor an id on that page
//   size       gzipped JavaScript per page: 100 KB at first load, 150 KB with every dynamic import
//   text       every page has its own <title> and meta description, and text inside <main> without JavaScript
//   json-ld    every page carries at least one JSON-LD block, and every block parses and names an @type
//   sitemap    sitemap.xml and llms.txt list every page and no page outside the build
//   robots     env mvp: every page sends noindex and robots.txt disallows every crawler
//              env production: no page sends noindex, and robots.txt lets GPTBot, ClaudeBot and PerplexityBot in
import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { join, relative, posix } from 'node:path';
import { gzipSync } from 'node:zlib';
import { pathToFileURL } from 'node:url';

export const DEFAULTS = { env: 'mvp', firstKb: 100, lateKb: 150 };
const AI_CRAWLERS = ['GPTBot', 'ClaudeBot', 'PerplexityBot'];

export function parseArgs(argv) {
  const opts = { ...DEFAULTS, dist: 'dist' };
  const rest = [...argv];
  while (rest.length) {
    const a = rest.shift();
    if (a === '--env') opts.env = rest.shift();
    else if (a === '--first-kb') opts.firstKb = Number(rest.shift());
    else if (a === '--late-kb') opts.lateKb = Number(rest.shift());
    else if (a.startsWith('--')) throw new Error(`unknown flag ${a}`);
    else opts.dist = a;
  }
  if (!['mvp', 'production'].includes(opts.env)) throw new Error(`--env must be mvp or production, not ${opts.env}`);
  for (const k of ['firstKb', 'lateKb']) if (!Number.isFinite(opts[k]) || opts[k] <= 0) throw new Error(`--${k} must be a positive number`);
  return opts;
}

const walk = (dir, onFile) => readdirSync(dir, { withFileTypes: true }).forEach((e) => {
  const f = join(dir, e.name);
  e.isDirectory() ? walk(f, onFile) : onFile(f);
});

const pagePath = (dist, f) => '/' + relative(dist, f).replace(/(^|\/)index\.html$/, '').replace(/\.html$/, '');
const strip = (html) => html.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<style[\s\S]*?<\/style>/g, '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const attr = (tag, name) => tag.match(new RegExp(`\\s${name}="([^"]*)"`))?.[1];

// Every page in the build: its path, html, ids, and the files that exist beside it.
export function readBuild(dist) {
  const pages = new Map();
  const files = new Set();
  walk(dist, (f) => {
    files.add('/' + relative(dist, f));
    if (!f.endsWith('.html')) return;
    const html = readFileSync(f, 'utf8');
    pages.set(pagePath(dist, f), { html, ids: new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1])) });
  });
  return { pages, files };
}

export function checkLinks({ pages, files }) {
  const refused = [];
  const external = /^(https?:\/\/|mailto:|tel:)/;
  for (const [page, { html }] of pages) {
    for (const [, raw] of html.matchAll(/<a\s[^>]*?\bhref="([^"]*)"/g)) {
      const href = raw.replaceAll('&amp;', '&');
      if (external.test(href)) continue;
      if (!href.startsWith('/') && !href.startsWith('#')) { refused.push(`links ${page}: cannot place "${href}"`); continue; }
      const [path, anchor] = href.split('#');
      const target = path === '' ? page : path.replace(/\/$/, '') || '/';
      if (!pages.has(target) && !files.has(target)) { refused.push(`links ${page}: "${href}" reaches no page in the build`); continue; }
      if (anchor !== undefined && anchor !== '' && pages.has(target) && !pages.get(target).ids.has(anchor)) refused.push(`links ${page}: "#${anchor}" is no id on ${target}`);
    }
  }
  return refused;
}

export function checkSize({ pages }, dist, { firstKb, lateKb }) {
  const refused = [];
  const gz = (text) => gzipSync(text).length;
  const parsed = new Map();
  const read = (file) => {
    if (parsed.has(file)) return parsed.get(file);
    const entry = { size: 0, static: [], dynamic: [] };
    parsed.set(file, entry);
    const path = join(dist, file);
    if (!existsSync(path)) { refused.push(`size ${file}: imported but not in the build`); return entry; }
    const code = readFileSync(path, 'utf8');
    entry.size = gz(code);
    const place = (spec, kind) => {
      if (!/^\.{1,2}\//.test(spec)) { refused.push(`size ${file}: ${kind} import of "${spec}" is not a file in the build`); return; }
      entry[kind].push(posix.normalize(posix.join(posix.dirname(file), spec)));
    };
    const q = `["'\`]([^"'\`]+)["'\`]`;
    for (const [, spec] of code.matchAll(new RegExp(`\\bfrom\\s*${q}`, 'g'))) place(spec, 'static');
    for (const [, spec] of code.matchAll(new RegExp(`\\bimport\\s*${q}`, 'g'))) place(spec, 'static');
    const dynamic = [...code.matchAll(new RegExp(`\\bimport\\(\\s*${q}\\s*\\)`, 'g'))];
    for (const [, spec] of dynamic) place(spec, 'dynamic');
    const calls = [...code.matchAll(/\bimport\(/g)].length;
    if (calls !== dynamic.length) refused.push(`size ${file}: ${calls - dynamic.length} dynamic import(s) with a computed path`);
    return entry;
  };
  const closure = (starts, withDynamic) => {
    const seen = new Set(); const stack = [...starts];
    while (stack.length) {
      const f = stack.pop();
      if (seen.has(f)) continue;
      seen.add(f);
      const e = read(f);
      stack.push(...e.static, ...(withDynamic ? e.dynamic : []));
    }
    return seen;
  };
  for (const [page, { html }] of pages) {
    const entries = [];
    let inline = 0;
    for (const [, attrs, body] of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)) {
      if (/type="application\/ld\+json"/.test(attrs)) continue;
      const src = attr(attrs, 'src');
      if (src === undefined) { inline += gz(body); continue; }
      if (!src.startsWith('/') || src.startsWith('//')) { refused.push(`size ${page}: script ${src} is not a file in the build`); continue; }
      entries.push(src.slice(1));
    }
    const sum = (set) => [...set].reduce((n, f) => n + read(f).size, inline);
    const first = sum(closure(entries, false)) / 1024;
    const late = sum(closure(entries, true)) / 1024;
    if (first > firstKb) refused.push(`size ${page}: ${first.toFixed(1)} KB at first load, over ${firstKb} KB`);
    if (late > lateKb) refused.push(`size ${page}: ${late.toFixed(1)} KB with late loads, over ${lateKb} KB`);
  }
  return refused;
}

export function checkText({ pages }) {
  const refused = [];
  const titles = new Map(); const descriptions = new Map();
  for (const [page, { html }] of pages) {
    const title = strip(html.match(/<title>([\s\S]*?)<\/title>/)?.[1] ?? '');
    const description = [...html.matchAll(/<meta\s[^>]*>/g)].map((m) => m[0]).filter((t) => attr(t, 'name') === 'description').map((t) => attr(t, 'content'))[0];
    if (!title) refused.push(`text ${page}: no <title>`);
    else if (titles.has(title)) refused.push(`text ${page}: title "${title}" is also ${titles.get(title)}'s`);
    else titles.set(title, page);
    if (!description) refused.push(`text ${page}: no meta description`);
    else if (descriptions.has(description)) refused.push(`text ${page}: meta description is also ${descriptions.get(description)}'s`);
    else descriptions.set(description, page);
    const main = html.match(/<main\b[\s\S]*?<\/main>/)?.[0];
    if (!main) refused.push(`text ${page}: no <main>`);
    else if (strip(main).length === 0) refused.push(`text ${page}: <main> holds no text without JavaScript`);
  }
  return refused;
}

export function checkJsonLd({ pages }) {
  const refused = [];
  for (const [page, { html }] of pages) {
    const blocks = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)].filter(([, attrs]) => /type="application\/ld\+json"/.test(attrs));
    if (blocks.length === 0) { refused.push(`json-ld ${page}: no JSON-LD block`); continue; }
    blocks.forEach(([, , body], i) => {
      let data;
      try { data = JSON.parse(body); } catch (e) { refused.push(`json-ld ${page}: block ${i + 1} does not parse (${e.message})`); return; }
      const items = Array.isArray(data) ? data : data?.['@graph'] ?? [data];
      for (const item of items) if (!item || typeof item !== 'object' || !item['@type']) refused.push(`json-ld ${page}: block ${i + 1} has an item with no @type`);
    });
  }
  return refused;
}

export function checkSitemap({ pages }, dist) {
  const refused = [];
  const listed = (file, pattern) => {
    const path = join(dist, file);
    if (!existsSync(path)) { refused.push(`sitemap ${file}: missing from the build`); return null; }
    return new Set([...readFileSync(path, 'utf8').matchAll(pattern)].map((m) => { try { return new URL(m[1]).pathname.replace(/(.)\/$/, '$1'); } catch { refused.push(`sitemap ${file}: cannot place "${m[1]}"`); return null; } }));
  };
  for (const [file, pattern] of [['sitemap.xml', /<loc>\s*([^<\s]+)\s*<\/loc>/g], ['llms.txt', /\]\((https?:\/\/[^)\s]+)\)/g]]) {
    const found = listed(file, pattern);
    if (!found) continue;
    if (found.size === 0) refused.push(`sitemap ${file}: lists no page`);
    for (const page of pages.keys()) if (!found.has(page)) refused.push(`sitemap ${file}: does not list ${page}`);
    for (const path of found) if (path !== null && !pages.has(path)) refused.push(`sitemap ${file}: lists ${path}, which is not in the build`);
  }
  return refused;
}

export function checkRobots({ pages }, dist, { env }) {
  const refused = [];
  const noindex = (html) => [...html.matchAll(/<meta\s[^>]*>/g)].some((m) => attr(m[0], 'name') === 'robots' && /noindex/.test(attr(m[0], 'content') ?? ''));
  for (const [page, { html }] of pages) {
    if (env === 'mvp' && !noindex(html)) refused.push(`robots ${page}: an mvp build sends noindex, this page does not`);
    if (env === 'production' && noindex(html)) refused.push(`robots ${page}: a production build never sends noindex`);
  }
  const path = join(dist, 'robots.txt');
  if (!existsSync(path)) { refused.push('robots robots.txt: missing from the build'); return refused; }
  // Each group: the user agents it names and whether it disallows the whole site.
  const groups = [];
  for (const raw of readFileSync(path, 'utf8').split(/\r?\n/)) {
    const line = raw.replace(/#.*/, '').trim();
    if (!line) continue;
    const [, key, value] = line.match(/^([A-Za-z-]+)\s*:\s*(.*)$/) ?? [];
    if (!key) { refused.push(`robots robots.txt: cannot place "${line}"`); continue; }
    const k = key.toLowerCase();
    if (k === 'user-agent') {
      if (groups.at(-1)?.open) groups.at(-1).agents.push(value); else groups.push({ agents: [value], blocksAll: false, open: true });
    } else if (groups.length) {
      groups.at(-1).open = false;
      if (k === 'disallow' && value === '/') groups.at(-1).blocksAll = true;
    }
  }
  const blocked = (agent) => (groups.find((g) => g.agents.includes(agent)) ?? groups.find((g) => g.agents.includes('*')))?.blocksAll ?? false;
  if (env === 'mvp' && !blocked('*')) refused.push('robots robots.txt: an mvp build disallows / for every crawler');
  if (env === 'production') for (const agent of AI_CRAWLERS) if (blocked(agent)) refused.push(`robots robots.txt: production keeps ${agent} out`);
  return refused;
}

export function runAll(dist, opts) {
  const build = readBuild(dist);
  if (build.pages.size === 0) return [`${dist}: no pages found, so nothing was measured`];
  return [
    ...checkLinks(build), ...checkSize(build, dist, opts), ...checkText(build),
    ...checkJsonLd(build), ...checkSitemap(build, dist), ...checkRobots(build, dist, opts),
  ];
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const opts = parseArgs(process.argv.slice(2));
  const refused = runAll(opts.dist, opts);
  if (refused.length) {
    console.error(`Static checks refused ${refused.length}:\n` + refused.map((r) => `  ${r}`).join('\n'));
    process.exit(1);
  }
  console.log(`Static checks passed: ${readBuild(opts.dist).pages.size} pages (${opts.env}).`);
}
