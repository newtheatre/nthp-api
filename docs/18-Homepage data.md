---
type: task
status: done
---

# Homepage data

Web doc 30 §9.

## Stats

Extend `SiteStats` (`/index.json`): `venueCount, yearCount, firstYearId, latestYearId, showsWithImageCount, personWithHeadshotCount`, plus `count` of search documents (17).

## On this day

`GET /on-this-day/{MM}-{DD}.json` → `OnThisDayShow[]` `{id, title, yearId, year, primaryImage?, dateStart, dateEnd?}`; 366 files, empty arrays where no match. Match when `MM-DD` within `[dateStart, dateEnd ?? dateStart]` inclusive; day-precision dates only (`FuzzyDate.earliest()/latest()`). 837/1055 shows qualify. No `yearsAgo` — site computes.

## Poster pool

`GET /assets/posters.json` → `PosterItem[]` `{showId, showTitle, yearId, imageId}` for every show with a `primaryImage` (681). Deterministic order; no randomness in the API.

Spec entries for all three; tests for leap day and spanning-month ranges.
