# <nn> <What the change is, in a few words>

<What changes and why, written after reading the code it touches. Half a page at most. Name the buttons, labels and files by their real names. A note that changes a component lists every page that draws it: one feature stopped three final checks on a page that drew a changed card and that no note named.>

Screens: <screen names from the table in docs/design.md, `all <group>` for a group, or `none`. The screen of every page that draws a component this note changes is here.>
Risk: <none, or each of: money, authentication, secrets, migration, row writes>
Waits for: <none, or the numbers of the notes this one needs merged first>
Core design: <leave this line out, or "adds pattern <name>" or "rewrites screens". Needed for any change to docs/design.md.>
Prototype: <leave this line out, or the path or link of the approved prototype. Needed when the screens table is rewritten.>

## Done

- `<command>`: <what a pass proves>
- `<command>`: <one end-to-end check per screen named above>

## Tests

<One test file per done check, committed with this note. Each new test must fail on the code from before this note. Each rule this note adds (a check, a guard, a policy, a limit, a refusal) has a test that fails when the rule is removed: four of eight sampled reject reports named a rule with no such test. A new test that protects behaviour this note does not change starts its title with `keeps:`, so the red check skips it and the reviewer sees it.>
