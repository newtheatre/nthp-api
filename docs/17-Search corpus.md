---
type: task
status: done
---

# Search corpus

Web doc 30 §8. Site indexes with MiniSearch in a Worker; API ships fields, not a prebuilt index.

## Output

`SearchDocument` becomes a discriminated union on `type`, extending today's fields:

- show: `yearId, year, decade, season, seasonId, venueId?, venueName?, dateStart?`; `playwright` becomes a plain string (descriptor) not `PlaywrightShow`
- person: `hasBio, plaintext?` (bios currently not indexed), `graduationYear?, graduationDecade?, graduationEstimated?, careers?, course?, award?, showRoles?[], committeeRoles?[], showCount, yearIds?[]`
- venue: `city?, showCount, plaintext?`
- year: `decade, showCount`

Also: per-type files `/search/documents/{show,person,venue,year}.json` alongside the combined file; `SiteStats.searchDocumentCount` — `buildTime` already exists.

## Depends on

12 (seasonId), 13 (canonical role names), 16 (careers/course/award), 19 (year ids).

## Open questions

- None. `playwright` object→string accepted.

## Notes

- Named `searchDocumentCount`, not `count`: `SiteStats` already counts five other things under `*Count`, and a bare `count` says nothing about what is counted.
- The union is `SearchDocumentShow | SearchDocumentPerson | SearchDocumentVenue | SearchDocumentYear` discriminated on `type`, rendering as `oneOf` plus a `discriminator` mapping in the spec. `type` is required on every variant, not defaulted, so the dump's `exclude_unset` cannot drop the discriminator.
- Absent fields are omitted rather than sent as null, and empty lists are omitted too, keeping the corpus down.
- Person `showRoles` fold crew aliases into the canonical name from `_data/roles.yaml` and collapse every acting credit to `Actor`, matching `/roles/cast.json`; roles that file defines nowhere pass through as authored. `committeeRoles` use the API's own alias map. Roles named `unknown` are dropped from both.
- `dump_site_stats` moved to the post-dumpers: the count is only known once the parallel dumpers have filled the shared state.
- Person `plaintext` comes from the same markdown-to-plaintext pass as shows and venues. Two placeholder bios are nothing but an HTML comment, which that pass emits verbatim — pre-existing, and only visible now the bios are indexed.

## Result

4,666 documents: 3,491 people, 1,015 shows, 86 years, 74 venues. Combined 1.8 MB, person 896 KB, show 836 KB, venue 12 KB, year 8 KB, all uncompressed.
