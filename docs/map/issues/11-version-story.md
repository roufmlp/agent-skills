Status: resolved
Assignee: Abdul (wayfinder session 2026-10-30)
Type: prototype
Blocked by: 08, 09

# How the README tells the version story

## Question

What does a reader see in their first two minutes on the public repo? Draft a rough README outline that shows version 1, version 2, the measured reason for the change and the products built through it, then let Abdul react to the draft rather than describe one. "One repo that is safe to publish" put version 2 in `agent-skills` on top of version 1, which keeps the `v1` tag, so a reader can open both. The spec and this map go public with version 2. Product names, Orderflow included, may appear in the README; client names may not. The install section follows "How someone installs it": the one command, switching auto-update on, Python 3 for the hooks, and the Copilot app steps.

## Answer

The README opens with the story of the cut, written for a future employer who arrives from LinkedIn and judges on the first screen. The approved outline is [the prototype](../prototypes/11-readme-outline.md). Abdul turned down two other openings: one led with Orderflow, the other with the principle that agents forget reminders but cannot get past checks.

The first screen holds two short paragraphs, a table, the install command and one line on what the plugin holds. The first paragraph says what version 1 was and what it built: an autonomous pipeline with 33 hooks and an adversarial gate on every change, which built Orderflow in six weeks and 2,528 commits. Orderflow is finished and runs the orders of a real business, and the README says so. The second paragraph gives version 2 as two lanes and sets the target of a new product every two to four weeks. The title stays `agent-skills`, the repository's name.

The table counts what Abdul runs, not only what ships: 35 skills against 23, 11 of them his own against 5, 33 hooks against 6, and 16 agent definitions against 7. Its last row is the cost per shipped feature. "What version 1 cost, and where its time went" supplies the version 1 figure. The sentence "Then I measured where the time went and cut most of it" stays only if that ticket finds where the time went; if it cannot, the switch session rewrites the sentence around the Orderflow figures. The version 2 figure goes in once three products have graduated, measured the same way, and "How a regular audit keeps the workflow small" decides who measures it.

Below the first screen come, in order: how it works, the hooks that refuse, what the plugin holds, products, install, version 1, and credits. The products section lists graduated products only, never MVPs, and stays out of the README until the first product graduates. The version 1 section links the `v1` tag, keeps the five-issue case study and the record of how the model and effort levels were chosen, and links the map and the spec.

The first draft said Orderflow "still felt half done". That is wrong: it took long, and it is finished. The map's notes and "What the careful lane keeps" carried the same phrase and are corrected. Procurement stays out of the README, because a public page should not call Abdul's own work half done.

The plugin now depends on Matt Pocock's plugin rather than copying his skills. He wrote 18 of the 22 skills that "How someone installs it" put in the plugin, under the MIT licence, and version 1 linked to his skills without copying them. His pack is `mattpocock-skills` in Claude Code's official marketplace, which every install has, and a plugin can declare a dependency on a plugin in another marketplace ([plugin dependencies](https://code.claude.com/docs/en/plugins/dependencies)). So `workflow` carries Abdul's four skills, seven agents and four hooks, and the one install command brings both plugins. A friend who already has Matt Pocock's plugin gets no duplicate skills, and nobody syncs his skills by hand. Abdul accepted the price: Matt Pocock's changes reach him whenever the official listing moves, with no version range to hold them back. The details are in the note added to "How someone installs it".
