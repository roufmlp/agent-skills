# <Product> core design

One page that fixes the product's screens, patterns and modules. Every change follows it or changes it on purpose, with a `Core design:` line in the change note. Written at graduation, step 3 of `checklists/graduate-stop.md`.

## Screens

Every screen, one row each. The note check and the screenshot test read this table and nothing else of this file. Route is the path as the app serves it, with route groups such as `(signed-in)` left out. Group names a set a change note may name at once, as `Screens: all <group>`. A screen's baseline is `<slug>-<width>.png` in the screenshot spec's snapshot folder, where the slug is the screen name in lower case with each run of other characters replaced by one hyphen: "Order line" is `order-line-390.png`.

| Screen | Route | Group |
| --- | --- | --- |
| Sign in | /login | public |
| Home | / | signed-in |
| Orders | /orders | signed-in |
| Order | /orders/[id] | signed-in |

One line per group names the files a change to which touches every screen in the group, each path from the repo root:

Shared files for signed-in: src/app/(signed-in)/layout.tsx

## Patterns

One entry per pattern, each naming the check that refuses a second way of doing it. An entry without a check is not approved.

| Pattern | Check |
| --- | --- |
| <One button component, `src/controls/Button.tsx`> | `<npm run check:controls>` |

## Modules

The folders under `src/` and the imports each may make. ESLint's `no-restricted-imports` rule holds them; a rule ESLint cannot express gets a test.

| Module | May import |
| --- | --- |
| `app` | `controls`, `model`, `lib` |
| `controls` | `lib` |
| `model` | `lib` |
