---
name: panel-review
description: STORM-style multi-perspective review of any draft — LinkedIn copy, CV, post, email, article. Use when you want a draft "run through the panel", reviewed from several expert angles, or judged against a target (job description, audience, publication) to produce a final draft.
---

# panel-review

Mechanism borrowed from Stanford's STORM (OVAL Lab, NAACL 2024): one reviewer
has blind spots; several distinct perspectives reviewing the same text
independently, followed by a disagreement map, catch what any single pass
misses. STORM's own panel (academic, economist, historian...) is built for
researching topics — here the panel is picked per artefact instead.

## Process

1. **Pin the target.** What is the draft, who must it land with, and what
   should the reader do after reading (shortlist, reply, follow, buy)? If a
   job description, brief or publication is supplied, that document is the
   yardstick and every persona scores against it.
2. **Pick 4-6 personas** for this artefact (defaults below). Fewer sharp
   personas beat many vague ones. Name each persona's incentive — what they
   personally gain or lose by acting on the draft.
3. **Launch personas as parallel subagents.** Each gets: the draft (file
   path), the target, the hard constraints, and its persona brief only —
   never another persona's output. Each returns: a one-line verdict per
   section, its top 5 issues ranked with the exact line quoted and a
   concrete fix, 2-3 things that must survive any edit, and outright cuts.
   Brief them to be blunt.
4. **Synthesise.** Three buckets: (a) issues 3+ personas raise — fix them;
   (b) disagreements — map them, decide each with a stated reason;
   (c) unique catches — judge on merit. Never resolve a disagreement by
   inventing a fact.
5. **Produce the final draft.** Apply the fixes, run the writingrules
   gut-check, and write a dated review file next to the draft containing
   the disagreement map, the decision log and the final text. Never delete
   the original.

## Default panels

- **Career copy** (LinkedIn, CV, cover letter): recruiter in the target
  market · hiring manager for the target role · sceptical peer at the same
  level · search/ATS lens · writing editor.
- **Posts and articles**: the actual target reader · sceptical domain
  expert · "so what" lens (why should a stranger care) · writing editor.
- **Against a job description**: career panel above, each persona scoring
  requirement-by-requirement against the JD.
- **Outreach / asks** (recommendation requests, cold messages): the
  recipient · the recipient's sceptical colleague · writing editor.

## Hard rules

- Constraints travel with every persona verbatim: no invented facts; whatever
  project-specific rules apply (for career copy, typically: titles and dates
  literal, nothing published that is not yet public); writing follows your own
  writing rules (mine: [`steering/writingrules.md`](../../steering/writingrules.md)).
- Personas advise on selection and framing only — a persona suggesting a
  fabricated number or credential is overruled in synthesis, not obeyed.
- The search/ATS persona may only surface terms the draft's facts already
  support.
- Output is a recommendation plus a final draft; the source file is edited
  only when the human has asked for the edit, not just the review.
