---
type: task
status: done
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

Q: Threshold 8: agree, or derive from data (histogram of largest gaps across all ids)?
A: Agree
Q: Skip documented people entirely, or still report when the document has no `graduated` to anchor to?
A: Still report

## Results

`validate.check_merged_people`, lint check `merged-people`, severity worth
fixing. `MERGE_GAP_YEARS = 8` as decided; a documented person is skipped only
where `graduated` is set and every cluster lies within `graduated ± 6`, and
`--verbose` lists those skipped ids with their spans and graduation year (a new
optional `note` on `Check`, rendered under the explanation).

Against content at 2026-08-23: 8 findings, lint total 646.

| Id                    | Clusters                      | Credits |
| --------------------- | ----------------------------- | ------- |
| `alan_jones`          | 1961 and 1975                 | 3       |
| `alison_mackay`       | 1968 and 1977                 | 2       |
| `dave_anderson`       | 1975 and 1994                 | 2       |
| `matt_wilson`         | 2002-2003 and 2022            | 4       |
| `michael_hyde`        | 1950 and 2001                 | 3       |
| `rachel_brook`        | 1959 and 1994                 | 2       |
| `technical_committee` | 1955 and 1964-1965            | 3       |
| `unknown`             | 1965-1970, 1999-2013 and 2023 | 12      |

The last two are sentinel ids rather than people; left in, as suppressing them
would hide a real id that happened to be named that way.

No documented person was skipped: nothing in the archive has a document, a
`graduated` year and two clusters that year vouches for. The suppression is
built and tested but currently inert.

### Calibration

Three of the four known true positives are caught — `alan_jones` (gap 14),
`alison_mackay` (9), `dave_anderson` (19).

**`sam_morris` is missed, and the threshold is not the reason.** Their credits
are 2005–2007, then a single 2011 `freshers_fringe` credit, then 2016–2019: the
largest gap is 5, because the 2011 credit bridges the two careers. No threshold
that catches this stays useful — 5 would take in six more ids, and the 2011
credit would still have to be assigned to one Sam or the other by hand. Left as
a miss rather than tuned; task 29's double-space list is the authority for this
one.

The gap histogram over 3,647 credited ids supports 8: 2,556 ids have no gap at
all, the tail runs 1 (918), 2 (133), 3 (21), 4 (5), 5 (3), 6 (2), 7 (1), then
nothing until 9 (2), 14, 19 (2), 29, 35, 51. Eight sits in an empty band, so the
findings are the far tail rather than a cut through a continuum.
