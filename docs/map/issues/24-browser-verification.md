Status: resolved
Assignee: Abdul (wayfinder session 2026-11-01)
Type: grilling
Blocked by: 15, 19, 21

# What the verifier checks in the browser

## Question

Version 1's verify gate opened the running app, walked each issue's acceptance path and rejected on what it saw. Version 2's verifier does less in the browser. It walks the product's main flow, compares every baseline screen with its screenshot, and runs the end-to-end specs for the screens the note changes, as "How a feature with several change notes runs without Abdul" and "How the careful lane keeps the test suite fast and trusted" set out. The reviewer reads the diff and never opens the app.

That leaves the note's own new actions untested in a browser unless its done checks happen to include an end-to-end spec for them. A new export button on a settings page, off the main flow, can ship with nobody clicking it. Decide whether the verifier also walks the note's own actions in the running app, or whether every note that changes a screen must carry an end-to-end spec as a done check, which the verifier already refuses to accept if it passes before the work.

A new screen has a second gap. The screenshot baselines come from graduation, as "How the careful lane keeps every slice aligned to the core design" ruled, so a screen added later has none. Decide who approves how a new screen looks, when its baseline is taken, and whether a new screen needs a prototype the way a redesign does. Abdul approves by looking at screens, not by reading code, and a run of several notes happens without him.

The fast lane faces the same question in a smaller form: its one build session walks the main flow and Abdul approves the prototype-against-MVP page at the end. Say whether anything changes there.

The lighter option is the done-check rule alone: a note that changes a screen carries an end-to-end spec, and a new screen's first screenshot becomes its baseline on Abdul's approval of the feature report. An answer heavier than that says what the lighter one would cost.

## Answer

Someone clicks every new button. Each note that changes a screen carries an end-to-end spec as a done check, and the note's verifier also walks the note's own new and changed actions in the running app, trying to break them. A new screen gets its baseline from its first screenshot, and Abdul approves it by looking at the feature report before he pushes.

The spec rule alone was the lighter option, and version 1 shows what it misses. Of 227 verify verdicts, 48 were rejects, and in 16 of those the verifier saw the fault by driving the app: a total lost on reload, focus lost after a key press, a label drawn twice. Five of the 16 sat off the main flow. In 9 of them the implementer's own spec passed while the walk found the fault, because the spec never tried a second road, a reload, scrolling or two fast clicks. A rule that only asks for a spec would not have forced those cases. In version 2 the done checks are written in the interview, before the code exists, which may close part of that gap, but nobody has measured it. The counts and examples are in [the verify reject research](../research/24-verify-rejects.md).

**Which notes need a spec.** Each note carries a "Screens:" line, written in the interview. The screens part of the core design names each screen's route. Two existing checks refuse:

1. The check that runs every done check on today's code before the run starts also refuses a note that names a screen and has no end-to-end done check. That check already refuses a done check that passes before the work, so the spec has to fail first.
2. The note check refuses a diff that touches a screen's route folder when the note's "Screens:" line does not name that screen.

**The walk.** After the scoped run, the verifier walks each action the note adds or changes. It writes throwaway Playwright cases with hostile data: a reload, a second road to the same state, two fast clicks, the 390-pixel width, the empty state and the error state. It rejects on what it sees, and a reject is a strike, as for any verifier reject. The verifier already starts the app for the scoped specs and screenshots, so the walk adds time but no new start. That time is not measured; version 1's verify step took 14 minutes on average, and no record splits the walk out. The audit's cost row measures it after the first features. The reviewer still reads the diff and never opens the app.

**What the walk leaves behind.** A case that finds a fault goes into the reject report, and the next implementer commits it as a spec that the fix must make pass. The walk has already shown that it fails on the code before the fix. The other cases are thrown away, so the suite grows only by the faults it found and the suite budget is spared.

**One-note changes.** A change of one note runs as one `/goal` session with no separate verifier. Before it merges, the session starts a fresh verifier subagent from the agent file `/build-feature` already ships, and that verifier walks the note. A builder checking its own work is how 9 of version 1's 16 browser faults got past a passing spec.

**New screens.** A new screen built from approved patterns needs no prototype; the pattern checks already refuse a second way of doing a thing. A new screen that needs a new pattern needs a prototype, which Abdul approves in the interview, where that pattern already stops for his approval. Every screen listed in the screens part of the core design has a baseline, not only the main-flow screens, so the test reads that list and nobody keeps a second one. Each screen adds about two seconds per width, about two minutes for 30 screens in the final check. A new screen's first screenshot, taken by the final verifier, becomes its baseline, and the merger commits it with the feature. Abdul looks at it in the feature report before the push, which is already his step. If he dislikes it, a follow-up note changes it, and the note check sees a changed baseline that the note names. Holding the merge to local main until he approves would stop a finished run until he is at the keyboard.

**The feature report.** It gains a screens section: each new screen at 390 and 1280 pixels, and each changed screen before and after, with each difference marked. The final verifier already takes every screenshot, so the report only lays them out. It uses the same layout as the fast lane's side-by-side page.

**The fast lane.** One change. The side-by-side page of prototype and MVP marks each screen the prototype did not have as "new", so Abdul sees every screen nobody approved. Nothing else changes: an MVP holds nothing real, and when Abdul uses it once, he does the clicking. A done check for every action would push the brief past a page.

**Budget.** The walk is part of the verifier's agent file and the "Screens:" refusals extend checks that already run, so no new tool arrives.

`CONTEXT.md` now defines hostile walk.

Changed by "Where the note check lives, and baselines for changed screens" (2026-11-01): a "Screens:" line may name a route group, and a change to a shared file in the group counts as touching each of its screens. Changed baselines are retaken by the final verifier and approved by Abdul's push, as new ones are.
