// The screenshot test: every screen in the screens table of docs/design.md, at 390 and 1280
// pixels, against its baseline. The note check reads the same table, so nobody keeps a second list.
//
// Copied to `e2e/screens.spec.ts` at graduation (step 4 of checklists/graduate-stop.md). The
// product writes `e2e/screens-seed.ts` beside it, the one product-specific part: it exports
// `prepare()`, which seeds the data every screen shows and returns the cookies that sign the
// browser in, the values for each `[param]` in a route, the one instant every screen is shot at,
// and the selectors to mask (a count that drifts).
//
// The clock: `time` is required, and the spec fixes the browser's clock at it before each page
// loads, so a date, an hour or "3 days ago" the browser renders reads the same on every day and
// every machine. A date the SERVER renders is the product's: `prepare()` must start or point the
// local app at the same instant (an env variable its one ambient clock reads), or mask it. In the
// rehearsal 20 of 58 baselines drifted on the day after they were taken, on the same machine,
// because Home's date followed the real clock.
//
// A baseline is `<slug>-<width>.png` in this spec's snapshot folder; Playwright adds its own
// project and platform suffix after the width, which the note check ignores. A new screen has no
// baseline yet: `--update-snapshots --grep "<slug>"` takes it, and the final verifier is the role
// that runs that. A screen named by a change note is retaken the same way; every other screen must
// match.
import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type BrowserContext } from "@playwright/test";
import { prepare } from "./screens-seed";
// A product whose e2e folder wraps `test` (Orderflow's `failure-dump.ts`) takes the line above from there.

export const WIDTHS = [390, 1280] as const;
const HEIGHT = 900;

export interface Screen {
  name: string;
  route: string;
  group: string;
  slug: string;
}

export interface ScreensSeed {
  /** Cookies that sign the browser in, in Playwright's own shape (`url` or `domain` and `path`). */
  cookies: Parameters<BrowserContext["addCookies"]>[0];
  /** A value for each `[param]` or `[...param]` a route carries, by the param's name. */
  params: Record<string, string>;
  /** A whole path for a route, where two routes share a param name: `"/bills/[id]": "/bills/<uuid>"`. */
  routes?: Record<string, string>;
  /**
   * The instant every screen is shot at, with its zone: `"2026-01-05T09:30:00+04:00"`. The spec
   * fixes the browser's `Date` at it; the server's clock is the seed's to fix the same way.
   */
  time: string;
  /** Selectors masked before the screenshot: a count or a server-rendered date that still drifts. */
  mask?: string[];
}

/** "Order line" -> "order-line": lower case, each run of other characters one hyphen. */
export function slugOf(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

/** The rows of the first table under `## Screens`, in docs/design.md's shape. */
export function screensOf(markdown: string): Screen[] {
  const section = markdown.split(/^## Screens\s*$/m)[1]?.split(/^## /m)[0] ?? "";
  const rows = section
    .split("\n")
    .filter((line) => line.startsWith("|"))
    .map((line) => line.split("|").slice(1, -1).map((cell) => cell.trim()));
  return rows
    .filter((cells) => cells.length >= 3 && cells[0] !== "Screen" && !/^-+$/.test(cells[0]))
    .map(([name, route, group]) => ({ name, route, group, slug: slugOf(name) }));
}

/** `/jobs/[number]/confirm/[letter]` with its params filled; a missing param is an error that names it. */
export function fillRoute(route: string, seed: Pick<ScreensSeed, "params" | "routes">): string {
  const whole = seed.routes?.[route];
  if (whole !== undefined) return whole;
  const params = seed.params;
  return route.replace(/\[(\.\.\.)?([^\]]+)\]/g, (_, _spread, name) => {
    const value = params[name];
    if (value === undefined) throw new Error(`screens-seed.ts gives no value for [${name}] in ${route}`);
    return value;
  });
}

const design = readFileSync(path.join(process.cwd(), "docs", "design.md"), "utf8");
const screens = screensOf(design);

test.describe("screens", () => {
  let seed: ScreensSeed;

  test.beforeAll(async () => {
    seed = await prepare();
  });

  for (const screen of screens) {
    for (const width of WIDTHS) {
      test(`${screen.slug}-${width}`, async ({ page, context }) => {
        await context.addCookies(seed.cookies);
        await page.clock.setFixedTime(seed.time);
        await page.setViewportSize({ width, height: HEIGHT });
        await page.goto(fillRoute(screen.route, seed), { waitUntil: "networkidle" });
        await expect(page).toHaveScreenshot(`${screen.slug}-${width}.png`, {
          fullPage: true,
          animations: "disabled",
          mask: (seed.mask ?? []).map((selector) => page.locator(selector)),
        });
      });
    }
  }
});
