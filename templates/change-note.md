# <nn> <What the change is, in a few words>

<What changes and why, written after reading the code it touches. Half a page at most. Name the buttons, labels and files by their real names.>

Screens: <screen names from the table in docs/design.md, `all <group>` for a group, or `none`>
Risk: <none, or each of: money, authentication, secrets, migration, row writes>
Waits for: <none, or the numbers of the notes this one needs merged first>
Core design: <leave this line out, or "adds pattern <name>" or "rewrites screens". Needed for any change to docs/design.md.>
Prototype: <leave this line out, or the path or link of the approved prototype. Needed when the screens table is rewritten.>

## Done

- `<command>`: <what a pass proves>
- `<command>`: <one end-to-end check per screen named above>

## Tests

<One test file per done check, committed with this note. Each new test must fail on the code from before this note. A new test that protects behaviour this note does not change starts its title with `keeps:`, so the red check skips it and the reviewer sees it.>
