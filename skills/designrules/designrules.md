# designrules

> How Abdul wants design work done. Applies to anything visual: websites, app UI,
> landing pages, documents, slides, PDFs. Read before starting any design work.
>
> Distilled from three videos (July 2026): "Every UI/UX Concept Explained in Under
> 10 Minutes" (youtu.be/EcbgbKtOELY), "How To Build a Website SO Premium They Beg
> You To Buy" (youtu.be/7p-ZPK3GfI8), "The Psychology of Premium Websites"
> (youtu.be/f2mGqlLLqok). Agency sales pitches and sponsor segments discarded.
> This is a 2026 snapshot of taste, not physics. Revisit when it starts to feel dated.
>
> Precedence: an existing project design system or client brand guide beats these
> rules. These beat improvising. A design system earns that rank by being
> deliberate: tokens, chosen type and palette, states designed. Code that merely
> exists — a demo page's styles, one-off components — is a draft, not a system;
> these rules outrank it. Improve drafts in place: upgrade the shared element and
> every page gets the upgrade. Never fork a better duplicate beside the old one,
> and never treat "it already exists" as a reason it can't get better.

## The idea in one breath

Premium is a feeling built from two things: clarity and cared-for details. A visitor
decides in the first screen whether you're professional. Earn that with hierarchy,
whitespace and restraint, then keep earning it in the small moments: hovers, states,
transitions. Every element has a job. If it doesn't, it goes.

---

## Part 1 — First impressions (the psychology)

1. **The first screen decides.** Users judge a site in about 50 milliseconds and that
   judgment colours everything after (the halo effect). Design the hero harder than
   anything else. Pick the one feeling it should give (calm, confidence, excitement)
   and build the first screen around only that.
2. **Cut cognitive load before adding anything.** Brains read easy-to-process as
   trustworthy and high quality. Generous whitespace, one goal per section, predictable
   navigation. On every page ask: what can I remove? What is simple to the maker is
   still confusing to a first-time visitor.
3. **Small moments carry the memory.** People remember peaks and endings, not averages
   (the peak-end rule). Hover feedback, a gentle form confirmation, a smooth scroll
   transition: small peaks of delight that signal someone cared. Static pages read as
   lifeless; over-animated pages read as cheap. Motion should be felt, not noticed.

## Part 2 — Craft rules (the everyday checklist)

**Hierarchy.** Size, position and colour create importance; contrast between elements
is what makes hierarchy readable. Most important thing: biggest, boldest, nearest the
top. If everything is loud, nothing is.

**Spacing.** Work on a 4-point system (multiples of 4) so any gap can halve cleanly.
Around 32px between distinct blocks; pull related items closer together, since
proximity is hierarchy too. Whitespace matters more than grid dogma: the 12-column
grid is a guideline, useful mainly for repeating content and responsive behaviour.

**Typography.** One good sans serif is enough for almost any project; choose it
deliberately, then stop fiddling. The wrong font is the fastest way to look cheap.
Large headings: tighten letter-spacing by 2 to 3 percent and drop line-height to
110 to 120 percent. Cap the type scale: about six sizes on a landing page, fewer and
smaller (rarely above 24px) in dense product UI. Body text runs 45 to 75 characters
a line, about 66 as the sweet spot (Bringhurst) — a `max-width` on prose costs nothing.

**Colour.** Start from one primary, usually the brand colour; lighten it for
backgrounds, darken it for text, and you're halfway to a proper ramp. Semantic colours
keep their meaning: blue for trust and information, red for danger, yellow for
warning, green for success. Colour is for purpose, never decoration.

**States and feedback.** Every interactive element ships with default, hover,
active and disabled states, plus loading where data is involved. Inputs also need
focus and error (message, not just a red border). Every user action gets a visible
response; a click into silence is a bug.

**Screen states.** Whole screens have states too. Design every view five times:
ideal, empty, loading, error, and partial (a few rows, not enough to look alive) —
Scott Hurff's "UI stack". The empty state is the first thing a new user ever sees,
so it does onboarding work: say what belongs here and give the button that creates
the first one.

**Tables and data.** Numbers right-aligned in tabular (fixed-width) figures so
magnitudes line up; text left-aligned; centred columns are for nothing. Headers
label quietly — small, muted, not bold-and-shouting. In work tools density is a
feature: tighten row padding before you cut columns, keep row hover on, and let
rows carry a quiet zebra or divider, never both. Show the precision the task needs
and no more. Charts obey the same hierarchy rules as everything else: label the
data directly and drop the legend when you can.

**Icons and buttons.** Size icons to the text line-height they sit beside, then
tighten the gap. Ghost buttons (no background until hover) for secondary actions.
Button padding: horizontal roughly double the vertical.

**Shadows.** Most shadows are too strong. Low opacity, high blur. Depth follows
elevation: cards get whispers, popovers get more. If the shadow is the first thing
you notice, it's wrong.

**Dark mode.** No shadows in the dark; create depth with surfaces lighter than the
background. Mute borders and bright chips (drop saturation, flip contrast to the
text). Deep purples, greens and reds are allowed; dark mode is not only grey and navy.

**Images and overlays.** Text over an image never sits on a flat full-screen dim;
use a linear gradient into a readable background, with progressive blur when you
want it modern. An image is also the cheapest hierarchy win a card can get.

**Signifiers.** The UI should explain itself: containers group what belongs together,
selected and inactive states are visibly different, hovers and tooltips reveal what
things do. If it needs instructions, redesign it.

## Part 3 — Premium website rules (marketing pages)

1. **Bespoke beats generic.** Custom graphics with a job (break up content, guide the
   eye) instead of stock photos and free icon soup. A graphic that doesn't match the
   brand's tone is worse than no graphic.
2. **Brand kit before pages.** Intentional logo, a cohesive palette where the colours
   work together rather than five that work alone, and a deliberately chosen font.
   Everything else builds on that foundation.
3. **Structure is a journey.** Every page has a purpose and leads somewhere; the path
   from landing to action is obvious. One clear call to action, easy to find, easy to
   take, never buried in the footer. Sane sitemap, page hierarchy and internal links
   serve humans and search engines alike.
4. **Keep it alive.** A site the owner can update stays fresh; a stale site reads as
   an abandoned business.
5. **Fast is premium.** A slow page undoes every craft rule above it. Targets from
   Google's Core Web Vitals: largest content paint under 2.5 seconds, interaction
   response under 200 milliseconds, no visible layout shift (CLS under 0.1). In
   practice: images sized and compressed, dimensions reserved so nothing jumps, and
   skeletons rather than spinners — a skeleton promises structure, a spinner
   promises waiting.

## Part 4 — Signs of AI/template design (things that scream "nobody designed this")

The design twin of the writing rules' anti-AI checklist. Every item is a default
to refuse:

- **The AI startup uniform.** Near-black background, purple-to-blue gradient, one
  neon accent, Inter or Space Grotesk. Any one is fine; the full costume is a tell.
- **Gradient text on the hero's key word.** The single most recognisable tell.
- **The identikit hero.** Pill badge ("✨ Now in beta") above a centred headline,
  grey subline, two buttons (one filled, one ghost). Earn a different layout.
- **Bento grids by reflex.** One is a layout choice; every section a bento is a tell.
- **Glassmorphism everywhere.** Blur cards on gradient blobs. Depth should come from
  hierarchy, not frost.
- **Emoji as icons.** 🚀 in a feature card reads as "no icon budget". Same for the
  sparkle ✨ meaning "AI".
- **Three identical feature cards**, each icon-title-blurb, same length, same shape:
  the design version of the writing rules' rule-of-three tic.
- **Floating 3D blobs, orbs and meaningless abstract shapes.** A graphic without a
  job goes.
- **Decoration in motion**: animated counters, logo marquees, tilt-on-hover cards,
  scroll-jacking. Motion is felt, not noticed.
- **Everything centred.** Centred layouts are for moments; left-aligned is for
  reading. A page with no left edge has no spine.

The common thread: these are defaults reached for instead of decisions made. The fix
is never "use a different template" — it's Part 2: hierarchy, spacing, one palette,
elements with jobs.

## Borrowed from the canon (Nielsen Norman Group's usability heuristics)

The videos skipped three rules that have held since 1994. They mostly apply to
product UI rather than marketing pages:

- **Familiar beats clever.** People spend most of their time on other sites and
  apps, so they arrive trained. Use the conventions they already know (Jakob's law);
  make them learn a new pattern only when it genuinely pays.
- **Always leave the exit open.** Cancel, back, undo, close: clearly visible, never
  a dead end. Undo beats an "are you sure?" popup.
- **Prevent errors instead of reporting them.** Good defaults, constraints that make
  the wrong input impossible, confirmation only for the genuinely destructive. When
  an error does happen, say what went wrong and how to fix it, in plain words. And
  show options rather than making people remember them: recognition over recall.

## Not from the videos, but non-negotiable

None of the three videos mentioned accessibility, which is the one gap worth closing
here, with the actual numbers so it's checkable rather than vibes: body text keeps
4.5:1 contrast against its background; large text (24px+, or 19px bold) and
meaningful UI parts like icons and input borders keep 3:1 (WCAG 2.2, SC 1.4.3 and
1.4.11). Focus states stay visible for keyboard users. Touch targets: 24px is the
WCAG floor, 44px is comfortable (Apple's HIG). Animation respects
prefers-reduced-motion. Premium that excludes people isn't premium.

## Gut-check before shipping any design

1. What feeling does the first screen give in half a second? Is it the intended one?
2. What can I remove? (Ask twice.)
3. Does every element have a job?
4. Are all the states designed, or only the happy path?
5. Would I notice the shadow or the animation, or only feel it?
6. Does this follow the project's own design system first?

---

_Sources: the three videos above;
[NN/g's usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/);
[Scott Hurff's UI stack](https://www.scotthurff.com/posts/why-your-user-interface-is-awkward-youre-ignoring-the-ui-stack/);
[WCAG 2.2](https://www.w3.org/TR/WCAG22/) (SC 1.4.3, 1.4.11, 2.5.8);
[Apple HIG](https://developer.apple.com/design/human-interface-guidelines/accessibility);
[Core Web Vitals](https://web.dev/articles/vitals); Bringhurst; Refactoring UI
(Wathan & Schoger). Part 4 has no canonical source — community observation of
AI/template output, 2024-2026; it will date fastest, revisit it first._
_Last updated: 2026-07-23 — added Part 4 (AI/template tells), screen states, tables
and data, measure, WCAG/target numbers, Core Web Vitals; precedence now
distinguishes deliberate systems from drafts (drafts get upgraded in place)._
