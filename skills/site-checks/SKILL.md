---
name: site-checks
description: The shared done checks every `site` MVP runs before it is called done — Lighthouse, JavaScript size, links, titles and meta text, JSON-LD, sitemap with llms.txt and robots.txt, honeypot and rate limit, sideways scroll, axe. Use when a brief or a product CLAUDE.md names site-checks, when running a site's done checks, or before a site deploy.
---

Three scripts in `scripts/`, run from the product's folder after its build. Each refuses with one line per fault and exits 1; a refusal is work to do, never a number to loosen. Every check reads the whole build and refuses what it cannot place, so a page or a link the script cannot follow fails rather than passing unmeasured.

1. `node <this folder>/scripts/static.mjs dist` reads the built pages: links and anchors, gzipped JavaScript per page, a title and meta description of its own per page with text in `<main>` without JavaScript, JSON-LD on every page, `sitemap.xml` and `llms.txt` listing every page, and `robots.txt` with the noindex meta tag. Done when it prints `Static checks passed`.
2. `node <this folder>/scripts/browser.mjs --url <served address> dist` runs Lighthouse mobile and desktop on every page, axe at every width, and the sideways-scroll test. It loads `lighthouse`, `@playwright/test` and `@axe-core/playwright` from the product's `node_modules`, so those three are devDependencies of every site. Serve the build first (`astro preview`, or the host's equivalent). Done when it prints `Browser checks passed`.
3. `node <this folder>/scripts/form.mjs --url <enquiry endpoint> --honeypot <field>` posts the limit plus one times with the honeypot filled: each post up to the limit is refused with a 4xx other than 429, and the next one with 429. The server keeps that contract, and a post a bot makes counts against the limit, so this run sends nothing. Done when it prints `Form checks passed`.

The defaults are the numbers a site meets unless its brief says otherwise:

| Check | Default | Flag |
| --- | --- | --- |
| Build kind | `mvp` (noindex on every page, every crawler disallowed); `production` sends no noindex and lets GPTBot, ClaudeBot and PerplexityBot in | `--env` on static and browser |
| JavaScript at first load | 100 KB gzipped per page | `--first-kb` |
| JavaScript with late loads | 150 KB gzipped per page | `--late-kb` |
| Lighthouse | Performance 95 or more; Accessibility, Best Practices and SEO 100 | `--perf` (the three 100s have no flag) |
| Largest Contentful Paint | under 2.0 s | `--lcp` |
| Cumulative Layout Shift | under 0.05 | `--cls` |
| Widths for axe and scroll | 320, 768 and 1440 px | `--widths` |
| Enquiries per address before 429 | 5 | `--limit` |
| Browser | the installed Google Chrome | `--channel chromium` for Playwright's own |

A brief changes a number in one line of its part 5, naming the flag: "site-checks: `--first-kb 120`". The brief lists only the checks particular to its product; everything in this table is already covered. The product's `package.json` gets one script, `site-checks`, that runs the three commands with that brief's flags, so the check is one command for the build session and for anyone after it.

`node --test scripts/` runs this skill's own tests.
