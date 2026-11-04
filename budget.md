# Budget

The plugin's size on the day of the switch, 2026-11-04. `lib/check_budget.py` reads
this file and fails when the tree goes past it, in the Action on every push and once a
week. A skill, agent, hook or workflow added raises its number here in the same commit,
and an agent changes this file only with the owner's approval.

```
skills: 6
agents: 14
hooks: 4
workflows: 1
skill-file-lines: 250
```

A `SKILL.md` or agent file may not carry a date, the word "ruled" or "changed by":
those belong in the map or a change note, and a rule that cites its own history grows.
Two groups are exempt until parallel-hunt gets its smaller form, which is a session of
its own:

```
exempt-from-dates: skills/parallel-hunt/SKILL.md agents/parallel-hunt-*.md
exempt-from-lines: skills/parallel-hunt/SKILL.md
```
