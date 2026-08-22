---
type: task
status: todo
---

# Person identity

People are grouped by slugifying the credited name. Two people sharing a name collide, and the content repo's workaround is a double space in the name (`Emma  McDonald`). Jekyll turned that into a distinct filename (`emma__mcdonald.md`) so it worked; `python-slugify` collapses whitespace runs, so in this API the trick silently fails.

## Current state

Double-space credits in `content/_shows`: Emma McDonald (3), Sam Morris (7), Dave Anderson, Alan Jones, Alison Mackay (1 each). Only `_people/emma__mcdonald.md` exists as a document.

What happens today:

- `people.get_person_id` maps `Emma  McDonald` → `emma_mcdonald`, so the second Emma's three credits land on the first Emma's page, and the `emma__mcdonald` document (loaded by filename) has no credits.
- Sam Morris: two people merged into one virtual person with seven of the other's credits.
- Lint reports the rest as "people credited under two names" — the finding is a symptom, not the defect.

Nothing documents the double-space convention; `_data/defs/person-list.yaml` says only that a name "should be unique and match exactly across the site".

## Proposal

Make identity explicit instead of encoding it in whitespace.

1. **Optional `id` on credits.** `PersonRef` gains `id: str | None`. Credit id = `id` if set, else `slug(name)`. Same for `playwright`/`playwright_alias` credits (task 27 should carry it) and `_people/` documents (filename stays the id). Validation: `id` must match `^[a-z0-9_]+$`; an `id` with no `_people/` document is still a valid virtual person.
2. **Names are display text.** Drop "must be unique" from the person-list def; uniqueness is the id's job. Two people may share a name; the site disambiguates with headshots/years as it does for any ambiguous list.
3. **Build error on whitespace runs in names.** Once content is migrated, a double space is a defect (the old trick no longer does anything) — `models.PersonRef` validator rejects it, message pointing at `id:`.
4. **Content migration (content-repo PR).** For each double-space name: pick ids (`emma_mcdonald_2`, or better, a distinguishing id such as `emma_mcdonald_2014` by graduation year), rewrite the credits as `- name: Emma McDonald\n  id: emma_mcdonald_2`, rename `emma__mcdonald.md` → `emma_mcdonald_2.md` with `title: Emma McDonald`. Sam Morris et al. need a human to decide which credits belong to which person — the task's output should list them with years so the editor can split them.
5. **Lint, not build, for the remaining cases.** `person-names` finding (variant spellings, one id, no document) stays in lint. Add a lint check for a person id whose credits span an implausible range (> ~8 years) as a hint that two people are merged — catches future collisions without an explicit marker.
6. **Schema/docs.** Task 28's content schema and editor docs describe `id` and the rule "same person, same id; same name, different person → set `id`".

## Why not keep the double space

Whitespace-as-data is invisible in editors, gets normalised by formatters, and nothing validates it. Preserving it would mean a custom slug that keeps whitespace runs — compatible with old Jekyll filenames, but it perpetuates the hack and still leaves the Sam Morris split undocumented.

## Transition

Until the content PR lands, the API is wrong for the five names above. Interim option if the content PR is slow: a `PERSON_ID_OVERRIDES` mapping in the content config (task 22) from exact credited name to id. Prefer doing the migration and skipping the interim.

## Questions

- Id scheme for namesakes: numeric suffix or year of graduation/first credit?
- Should `id` be allowed on a credit where `person: false`? Proposal: no, reject.
- Does the new site need a stable id for the _first_ Emma McDonald to remain `emma_mcdonald`? Proposal: yes, never rename existing ids.
