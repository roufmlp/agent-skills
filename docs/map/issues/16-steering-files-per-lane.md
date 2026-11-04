Status: resolved
Assignee: Abdul (wayfinder session 2026-10-31)
Type: grilling
Blocked by: 08

# Which steering files each lane loads, and the new CLAUDE.md

## Question

Most of today's global rules (the chain, the direct road, the decisions queue, the daily brief, the three heavy skills) assume the chain, and every session loads them. Which steering files does each lane load: CLAUDE.md, memory, the design, code, writing and question rules, and the other steering skills? What shape does the new global CLAUDE.md take, and which of today's rules move, shrink or retire? Rewriting the content of the design and code rules is out of scope; this ticket decides only what loads where. "What the careful lane keeps" retired the chain, the decisions queue and daily-brief, and kept the rules pointers in the toolbox. "One repo that is safe to publish" retired the sync step, so today's "Public skills repo" rule retires with it. CLAUDE.md, the rules files and memory stay in `~/.claude/`, out of the public repository. The coderules and designrules pointer skills are public but read their rules from `~/.claude/`, which a friend does not have; `agent-skills` already carries copies in its `steering/` folder. Where those pointers point is for this ticket. Abdul also uses the GitHub Copilot app at work. It installs the same plugin, skills and agents only, and reads nothing in `~/.claude/`, so which rules load there is for this ticket too. coderules-gate ships, so where the code rules live decides what it checks.

Changed by "What happens to Orderflow" (2026-10-31): two more steering texts change at Orderflow's switch. Orderflow's own CLAUDE.md carries chain sections (after a run, the evening check, prototype fidelity and where pending items go), and the global CLAUDE.md's exception for "the OrderFlow report job" lets that job start a fix on its own. At the switch the job only sorts reports and drafts a change note for each bug, and a fix starts when Abdul asks. Where the replacement rules live is for this ticket.

Changed by "How the careful lane keeps every slice aligned to the core design" (2026-10-31): each product now has a core design at `docs/design.md`, which every build session and `/code-review` read. Where the pointer to it lives, the product's CLAUDE.md or elsewhere, is for this ticket.

## Answer

Each set of rules becomes the body of its own skill, the lane rules move into each product's `CLAUDE.md`, and the global `CLAUDE.md` keeps only the rules that hold in every session, at about 80 lines.

**The rules.** The code rules become the body of the `coderules` skill and the design rules the body of `designrules`, and both ship in the plugin. Claude Code keeps only a skill's name and description in context, about 100 tokens each, and loads the body when the skill starts, so a code session never loads the design rules and the cost matches today's pointer skills without the extra file read. writingrules takes the same form and stays private in `~/.claude/skills/`. The other copies retire: the CoWork vault masters, `~/.claude/coderules.md` and `designrules.md`, and the `steering/` folder of `agent-skills`, whose copies had already drifted from `~/.claude/` by 31 October. If CoWork needs the rules, it installs the same plugin. `coderules-gate` stops naming `~/.claude/coderules.md`, which a friend does not have, and checks for the plugin's `coderules` skill. A public copy kept in step by hand was rejected, because it brings back the sync step that "One repo that is safe to publish" retired.

**The lane rules.** The lane belongs to the product, so each product's `CLAUDE.md` carries it: a "Lane: fast" or "Lane: careful" line, that lane's steps and a pointer to `docs/design.md`. The brief session writes the file from a template of about 15 lines, and the graduation session rewrites it. The template ships in the plugin beside the brief template, so a friend's products get the same shape. Sessions outside a product, such as this map's, load no lane rules, and the built-in `/code-review` reads the core design through the pointer, because it reads the repo's `CLAUDE.md` files. A lane section in the global file was rejected: every session would pay for rules most of them never use.

**The global CLAUDE.md.** Today's 210 lines sort as follows.

- Kept: keep this file lean, ASD-STE100 reports, content written for Abdul, the design and code pointers, choose the simpler road, push only when Abdul says so, refuse or state a fact, never cite a bare identifier, and never hand Abdul a manual step.
- Shrunk: context hygiene, where "one issue per session" becomes "one change note per session" and the handoff rule stays. Pending actions, rewritten for the pending file below.
- Retired: the direct road (its five classes are now the careful lane's risk classes), the three heavy skills (parallel-hunt gets `disable-model-invocation: true`, so only the typed command starts it), the chain, the queue sweep at session close and the public skills repo.
- Moved: the exception for the OrderFlow report job goes to Orderflow's own `CLAUDE.md`, in its new form, where the job sorts reports and starts nothing.

**Pending actions and decisions.** daily-brief retires, so nothing would surface the `pending-on-abdul.md` files. They become one private file, `~/.claude/pending.md`, under two headings. "Do" holds actions, one numbered step each, written from the provider's current documents as today. "Decide" holds the questions that unattended sessions met: a session writes one there only when its default is hard to undo or the choice is Abdul's, and every other default goes in its end report alone. Each "Decide" entry gives the question, the default the session took, the case for and against each choice, and what reversing the default costs. The session-start hook prints both counts beside the machine preflight, for example "Pending: 2 to do, 1 to decide". Two lines in the global `CLAUDE.md` set this out and replace questionrules, which is already in the version 1 record. End reports alone were rejected, because a step that waits for days gets lost, and a file in the ideas repo was rejected, because the brainstorm page shows it only on the 1st and the 15th.

**The Copilot app at work.** It gets the code and design rules through the plugin's skills. It does not get the global `CLAUDE.md`, the ASD-STE100 rule, the writing rules or the pending file, because it reads nothing in `~/.claude/`. Nothing is added for work: an instructions file for Copilot would be a second copy to keep in step.

**Orderflow's CLAUDE.md.** The cleanup session of the switch rewrites five of its sections and adds the lane block at the top: "Lane: careful", the five lane steps and the pointer to `docs/design.md`. "Issue tracker" becomes "Change notes", which live in `changes/`. "After a run" retires. "The evening check" takes the rule that leaves the global file: the job sorts the reports, drafts a change note for each bug and starts a fix only when Abdul asks. "Screens are held to the frozen prototypes" gives way to the core design and the screenshot test. "The pending-on-abdul file" points at `~/.claude/pending.md`. The sections that state facts about the product, such as one database per tree and the two suites, stay.

**Memory.** The switch session makes one pass over the 11 project memory folders. It deletes each entry that names only a retired skill or file, such as the queue walk and the close rituals, rewrites an entry that is partly still true, and lists every deletion in its report. `rulings.md` stays in `~/.claude/` as the record behind the rules.

`CONTEXT.md` now defines pending file.

Changed by "Whether version 2 is built in two stages" (2026-11-01): stage one adds one line to today's global `CLAUDE.md`, ahead of the rewrite: a repo whose `CLAUDE.md` reads `Lane: fast` follows that file, not the chain or the pre-launch gate. The full rewrite still lands at the switch. The OrderFlow report job's exception changes now, because the job sorts reports from today.

Changed by "How the ideas repo and the brainstorm routine run" (2026-11-01): the global `CLAUDE.md` gains one line exempting pushes to `roufmlp/ideas` from the push rule. The ideas repo's own `CLAUDE.md` repeats the ASD-STE100 rule in one line, because the cloud session cannot read `~/.claude/`; the writing rules stay out of the cloud.

Changed by "How a product graduates, stops or switches over" (2026-11-01): the product `CLAUDE.md` template carries one more line: "When Abdul says *graduate* or *stop*, follow `checklists/graduate-stop.md` in the workflow plugin." The checklist file ships in the plugin beside the brief and `CLAUDE.md` templates, and is not a skill.

Changed by "How every version 2 session stays under 300k tokens" (2026-11-02): the global file keeps the context hygiene section, cut to eight lines with all five rules; the approved text is in that ticket.
