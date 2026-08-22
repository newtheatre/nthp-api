---
type: task
status: todo
---

# Merged people lint

Companion to task 29. When two people share a name and no one used the double-space trick (or it was lost), their credits merge into one id with nothing to flag it. Two people active in the same era are indistinguishable from the data; two people decades apart are not. A lint check should surface the latter.

## Signal

Per `person_id`, the sorted set of `target_year` from `PersonRole` (cast, crew, committee — `get_years_active` already builds this). One student's credits span roughly a degree: 3–4 years, up to ~6 for a PhD or staff. Find the largest gap between consecutive active years; a gap of `MERGE_GAP_YEARS` (propose 8) or more means two clusters, and two clusters is a merge until someone says otherwise.

Gap rather than total span: someone active 1994–2001 continuously is one long career, not two people; someone active 1975 and 1994 with nothing between is two.

## Known true positives to calibrate against

From task 29's double-space list, once the slug collapses them: Sam Morris (05/06–07/08 vs the other Sam), Dave Anderson (94/95 vs the other), Alan Jones (75/76), Alison Mackay (68/69). Check the gap is ≥ 8 for each; if any is smaller, the threshold is too high.

## Known false positives to expect

- Staff and long-serving technicians credited across decades — suppress where a `_people/` document exists with `graduated` set and all clusters fall within `graduated ± 6`, or via a per-document `same_person: true`/similar only if the count is small enough to justify a field. Prefer: list them in the finding, let the editor add a document, and skip people who **have** a document (a document implies a human has looked). Count the suppressed documented cases in the finding's verbose output so the suppression is visible.
- Alumni returning for an anniversary show or a fundraiser — rare, the finding hint says what to do: if genuinely one person, add a `_people/` document; if two, set `id` on one set of credits (task 29).

## Plan

1. `validate.check_merged_people`: for each undocumented `person_id` with ≥ 2 active years, compute the largest gap; finding when gap ≥ `MERGE_GAP_YEARS`. Value: id; hint: the clusters, e.g. `1975–1976 and 1994–1995 (4 credits)`.
2. Register as lint check `merged-people`, severity worth-fixing, copy: "Credits decades apart under one id — probably two people with the same name. If they are one person add a `_people/` document; if two, set `id` on the later credits."
3. `--verbose` lists the documented ids skipped with their gap.
4. Tests: synthetic roles — one person continuous 1994–2001 (no finding), two clusters (finding), two clusters with a document (skipped, listed in verbose), threshold boundary.
5. Run on content; record counts and the calibration result in this doc. Tune the threshold if the known cases fall through.
6. Sequence: lands before task 29's content migration so the editor splitting Sam Morris has the cluster list; needs nothing from 29 to run.

## Questions

- Threshold 8: agree, or derive from data (histogram of largest gaps across all ids)?
- Skip documented people entirely, or still report when the document has no `graduated` to anchor to?
