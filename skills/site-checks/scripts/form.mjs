// The shared form checks for a site: the honeypot and the rate limit on its enquiry endpoint. Refuses when either fails.
// Every post fills the honeypot, so a server that keeps its side of the contract sends nothing while this runs.
//
//   node form.mjs --url http://localhost:4321/api/enquiry --honeypot website [--limit 5] [--field name=Bot ...]
//
// The contract a site keeps (a brief changes a number in one line, which becomes a flag here):
//   honeypot    a post with the honeypot field filled is refused with a 4xx status other than 429
//   rate limit  the post after --limit posts from one address inside the window is refused with 429 (default 5,
//               so the sixth is refused). Posts a bot makes count, so the honeypot posts above use up the limit.
import { pathToFileURL } from 'node:url';

export const DEFAULTS = { limit: 5, honeypot: 'website', fields: {} };

export function parseArgs(argv) {
  const opts = { ...DEFAULTS, fields: { ...DEFAULTS.fields }, url: undefined };
  const rest = [...argv];
  while (rest.length) {
    const a = rest.shift();
    if (a === '--url') opts.url = rest.shift();
    else if (a === '--honeypot') opts.honeypot = rest.shift();
    else if (a === '--limit') opts.limit = Number(rest.shift());
    else if (a === '--field') {
      const [k, ...v] = (rest.shift() ?? '').split('=');
      if (!k || v.length === 0) throw new Error('--field takes name=value');
      opts.fields[k] = v.join('=');
    } else throw new Error(`unknown flag ${a}`);
  }
  if (!opts.url) throw new Error('--url is required: the endpoint the enquiry form posts to');
  if (!opts.honeypot) throw new Error('--honeypot must name the honeypot field');
  if (!Number.isInteger(opts.limit) || opts.limit <= 0) throw new Error('--limit must be a positive whole number');
  return opts;
}

// What each of the limit+1 statuses should have been, against what it was.
export function judge(statuses, { limit }) {
  const refused = [];
  if (statuses.length !== limit + 1) return [`form: expected ${limit + 1} posts, made ${statuses.length}`];
  statuses.slice(0, limit).forEach((s, i) => {
    if (s === 429) refused.push(`form post ${i + 1}: rate limited before the limit of ${limit}`);
    else if (s < 400 || s >= 500) refused.push(`form post ${i + 1}: honeypot filled, status ${s} instead of a 4xx refusal`);
  });
  if (statuses[limit] !== 429) refused.push(`form post ${limit + 1}: status ${statuses[limit]} instead of 429 after ${limit} posts`);
  return refused;
}

export async function run(opts, post = defaultPost) {
  const statuses = [];
  for (let i = 0; i <= opts.limit; i++) statuses.push(await post(opts.url, { ...opts.fields, [opts.honeypot]: 'https://bot.example' }));
  return { statuses, refused: judge(statuses, opts) };
}

async function defaultPost(url, fields) {
  const res = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(fields), redirect: 'manual' });
  return res.status;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const opts = parseArgs(process.argv.slice(2));
  const { statuses, refused } = await run(opts);
  console.log(`posts: ${statuses.join(' ')}`);
  if (refused.length) {
    console.error(`Form checks refused ${refused.length}:\n` + refused.map((r) => `  ${r}`).join('\n'));
    process.exit(1);
  }
  console.log(`Form checks passed: honeypot refused ${opts.limit} posts, the ${opts.limit + 1}th was rate limited.`);
}
