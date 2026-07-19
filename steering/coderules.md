# coderules

> How Abdul builds software, especially with AI at the keyboard. Read before writing
> or reviewing any code. Applies to every project unless that project's own docs say
> otherwise.
>
> Security section is grounded in the OWASP Top 10 (2025) and the official Supabase
> production checklist. One honest line before the list: no checklist makes a gap
> impossible. What prevents gaps is running the process every time with no
> exceptions. That is the actual promise: the gate below runs before every launch.

## The working rule: AI types, I decide

1. Every AI-written diff gets read before it lands. Review is not optional and not
   ceremonial; it is the whole safety model.
2. **The bypass check.** When a security control blocks a feature (RLS, validation,
   an authorisation check) and the AI "fixes" it by switching to an admin key or
   removing the check: stop. Fix the policy, never bypass it. This is the documented
   number-one failure in AI-built apps.
3. **No invented dependencies.** AI models suggest packages that don't exist or are
   typosquats. Before adding any package: check it's real, maintained, and popular
   enough to trust. Prefer zero new dependencies; every one is supply chain risk
   (OWASP 2025 puts supply chain at #3).
4. Build for today's requirement. No speculative abstraction, no config for
   imaginary futures. Simple code is auditable code.
5. Keep the business logic in one portable core, separate from screens and
   channels. It carries between stacks and it's the only part worth unit-testing
   heavily.

## Security: the non-negotiables

### Secrets and keys
- No secret ever reaches the client. Nothing sensitive behind `NEXT_PUBLIC_`, in a
  client component, a mobile bundle, or a public repo. The Supabase `anon` key is
  public by design; the `service_role` key bypasses every policy, so if it leaks
  the database is fully open.
- `.env*` stays gitignored. Secrets live in the platform's vault (Vercel or
  Cloudflare env settings), one set per environment, least privilege each.
- Never put secrets in URLs, logs, error messages, or AI prompts.
- MFA on every platform account: GitHub, Vercel, Cloudflare, Supabase, Meta,
  registrar. The accounts that deploy the app are part of the app.

### Database and data access
- **RLS on every table in the public schema, written the same day the table is
  created. No exceptions, no "later".** Default deny, then policies per role.
  This is Supabase's own going-live rule and most of their incident history.
- `service_role` only in code that provably never ships to a browser: route
  handlers, server actions, scheduled jobs. After build, grep the client bundle
  for keys before first deploy.
- Every query parameterised. String-built SQL does not pass review (injection,
  OWASP #5).
- Enforce SSL and set network restrictions in the database settings.
- Backups automated, and restore tested at least once per project. An untested
  backup is a hope.

### Who are you, what may you touch
- Authentication and authorisation happen on the server. Hiding a button is not
  access control. Broken access control has been OWASP #1 for years because
  everyone keeps trusting the client.
- Check object ownership on every request: not "is this user logged in" but "does
  this row belong to this user". Guessable IDs plus a missing ownership check is
  the most common API hole there is.
- Sessions in httpOnly, secure, sameSite cookies. Magic links single-use and
  expiring. Auth endpoints and anything that sends email or WhatsApp messages get
  rate limits; the key being public means anyone can hammer the endpoint, and you
  pay per message.

### Input, output, webhooks
- Validate every input on the server with a schema (zod or equivalent), whatever
  the client already validated.
- User content renders escaped. `dangerouslySetInnerHTML` with user data does not
  pass review (XSS).
- File uploads: allowlist of types, size cap, stored in object storage, never
  executed, never trusted by filename.
- Every webhook verifies its signature before doing anything: Telegram's
  `secret_token`, WhatsApp's `X-Hub-Signature-256`, payment providers' signing
  secrets. Unsigned calls are dropped. Handlers are idempotent, because providers
  retry.

### Platform, transport, dependencies
- HTTPS everywhere with HSTS. Security headers on: `X-Content-Type-Options`,
  `frame-ancestors` (or `X-Frame-Options`), and a CSP where the app allows it.
- CORS is an explicit allowlist. `*` does not pass review.
- Lockfile committed, versions pinned, `npm audit` (or Dependabot) on, unused
  packages removed. Update on a schedule, not only when something breaks.
- Errors fail closed. Users see a generic message; logs get the detail. Stack
  traces and SQL in production responses are a leak (OWASP 2025 added mishandled
  errors as its own category).
- Log auth events and admin actions; never log secrets or personal data. The test:
  if a breach happened last night, would anything tell you?

### AI-specific
- AI-generated code is an untrusted contribution until reviewed, same as a PR from
  a stranger.
- If the product itself calls an LLM: the model's output is untrusted input
  (prompt injection is real), user prompts are validated and rate-limited, spend
  caps are set, and no secret or customer record ever goes into a prompt.
- Production data never gets pasted into AI tools for debugging. Reproduce with
  fake data.

### When something leaks
Rotate the key first, investigate second. Every minute a leaked credential stays
valid is a minute the database is public. Then find how it leaked, then fix that
class of leak everywhere, not just the instance.

## Stack defaults for new projects
Next.js + Supabase (or Cloudflare Workers when it fits) + free tiers until real
customers. Magic-link auth. Deploy from day one so the thing is always demoable.
Domain logic in the portable core. RLS written with the schema, not after it.

## The pre-launch gate

Run before anything goes live with real users or real data, every time:

1. RLS enabled on every public table; policies reviewed against "default deny".
2. Grep the client bundle for `service_role` and any secret. Clean or no launch.
3. Log in as user A, try to read and write user B's rows by ID. Fail expected.
4. Hit every webhook endpoint unsigned. Rejection expected.
5. `npm audit` clean of criticals; lockfile committed.
6. Error pages in production show nothing internal.
7. Rate limits confirmed on auth and message-sending endpoints.
8. Backups on; one restore performed.
9. MFA verified on all platform accounts.
10. Supabase official production checklist walked top to bottom.

## Gut-check before shipping any code
1. Could someone read or write another user's row? Did I actually try?
2. Is there a secret anywhere a browser can see?
3. Did the AI bypass a control instead of fixing a policy?
4. Would this new dependency survive five minutes of scrutiny?
5. If this input were hostile, what breaks?

---

_Sources: [OWASP Top 10 (2025)](https://owasp.org/Top10/2025/);
[Supabase production checklist](https://supabase.com/docs/guides/deployment/going-into-prod);
[Supabase, Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)._
_Last updated: 2026-07-06 — initial version._
