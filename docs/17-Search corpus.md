---
type: task
status: todo
---

# Search corpus

Web doc 30 §8. Site indexes with MiniSearch in a Worker; API ships fields, not a prebuilt index.

## Output

`SearchDocument` becomes a discriminated union on `type`, extending today's fields:

- show: `yearId, year, decade, season, seasonId, venueId?, venueName?, dateStart?`; `playwright` becomes a plain string (descriptor) not `PlaywrightShow`
- person: `hasBio, plaintext?` (bios currently not indexed), `graduationYear?, graduationDecade?, graduationEstimated?, careers?, course?, award?, showRoles?[], committeeRoles?[], showCount, yearIds?[]`
- venue: `city?, showCount, plaintext?`
- year: `decade, showCount`

Also: per-type files `/search/documents/{show,person,venue,year}.json` alongside the combined file; `SiteStats.count` (document count) — `buildTime` already exists.

## Depends on

12 (seasonId), 13 (canonical role names), 16 (careers/course/award), 19 (year ids).

## Open questions

- None. `playwright` object→string accepted.
