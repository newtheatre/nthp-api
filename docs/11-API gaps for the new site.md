---
type: task
status: todo
---

# API gaps for the new site — overview

Source: `~/local/nthp-web-new/docs/30-Task-API-Gaps.md` (web doc 30). The new site does no site-side workarounds (nthp-web ADR-17), so everything here gates the site build. This doc reconciles web doc 30 with [03](03-Completeness%20review.md) and [01](01-Project%20plan.md) and splits the work into tasks 12–21.

Paths in web doc 30 are stale: package is `nthp_api/nthp_build/`, not `nthp_build/`.

## Task map

| Task                                                                | Covers                                                                                                                  | Web doc § |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | --------- |
| [12 Seasons](12-Seasons.md)                                         | seasons index/detail, `seasonId` on shows                                                                               | 1         |
| [13 Roles](13-Roles.md)                                             | committee roles index + all roles, crew roles from `roles.yaml`                                                         | 2         |
| [14 Shows index and sequence](14-Shows%20index%20and%20sequence.md) | `/shows/index.json`, prev/next, `missingFields`, `ignoreMissing`, `company_sort`                                        | 3, 11     |
| [15 Venue stubs](15-Venue%20stubs.md)                               | record for every referenced venue, sentinels, `venue_sort`, venue assets                                                | 4         |
| [16 Links and person fields](16-Links%20and%20person%20fields.md)   | `Link` schema everywhere, course/award/careers/news, `student`, `playwright_alias`/`_false`, year fellows/commendations | 6         |
| [17 Search corpus](17-Search%20corpus.md)                           | faceted `SearchDocument`, per-type files, person plaintext                                                              | 8         |
| [18 Homepage data](18-Homepage%20data.md)                           | `SiteStats` extras, on-this-day, poster pool                                                                            | 9         |
| [19 Year identifiers](19-Year%20identifiers.md)                     | `YYYY-YY` ids everywhere, `startYear`                                                                                   | 10        |
| [20 Image dimensions](20-Image%20dimensions.md)                     | width/height/date on every asset                                                                                        | 7         |
| [21 Trivia embedding](21-Trivia%20embedding.md)                     | embed trivia on show/person detail                                                                                      | 5         |

Suggested order (web doc §12): 13+12 → 14+15 → 16 → 17 → 18+19+21+14(prev/next) → 20. 19 is a breaking id change touching every dumper; doing it early (before 14/17/18 add new `yearId` fields) avoids a second pass — **recommended: do 19 first**, contrary to web doc ordering.

## Discrepancies with our docs

- **Year ids** (§10): not in any API doc. Plan Phase 4 "Y2K39 fix" is only half of it — `get_year_from_year_id` still parses `YY_YY` source dirs and must keep the Y2K fix; output side switches to `YYYY-YY`.
- **Trivia** (§5): 03 rates per-person trivia endpoints as "richer than Ruby"; web doc deletes them. Resolved in favour of embedding (one consumer, 120 items).
- **`student` / `decade`**: 03 says "derivable client-side"; ADR-17 forbids that. API emits both.
- **`buildTime`**: web doc §8/§9 proposes it; `SiteStats.build_time` already exists. Only `count` is new.
- **Dropped by web doc but flagged in 03**: `playwright_alias`/`playwright_false` (produce _wrong_ crew lists — included in 16), `company_sort` (14), `redirect_from`, `tour`, key-event images, `href_snapshot`, `city_sort`, `seats.yaml`. See open questions.
- **Roles source**: `_data/roles.yaml` is crew-only (31 roles, icons). Committee roles have no content-side definition; alias map must live in the API.
- **Image dimensions** (§7): ~1500 `sizedetails` calls depends on [06 SmugMug reliability](06-SmugMug%20reliability.md) (retries, Actions cache key never updating). 06 becomes a dependency of 20.
- **Caching**: S3 already emits `ETag` (MD5 for single-part PUT) and `Last-Modified`; nothing to build unless the deploy changes to multipart or a non-S3 host.
- **Strictness plan** (01 Phase 2 `extra="forbid"`, season enums): compatible. `SeasonDefinition` (12) is the season enum. `career:` singular (§6) must be an accepted alias, not a forbid failure.

## Decisions (2026-08-22)

- `YYYY-YY` (`2024-25`) ids, done first; content-repo directory rename deferred until after the new site launches.
- Old-URL redirects handled by the site repo; `redirect_from` stays unexposed.
- Include: `tour`, key-event `image`, `href_snapshot`. Exclude: `city_sort`, `seats.yaml`.
- Crew roles: delete vendored `CREW_ROLE_DEFINITIONS`, load `_data/roles.yaml` from content.
- Image dimensions: live SmugMug calls with a persistent cache; first run slow, accepted.
- `missingFields` values taken verbatim from `_plugins/show.rb` `missing_majority` (see 14).
- `unknown` season emitted as a record — useful for reconciliation.
- `/trivia/*` endpoints removed, not deprecated. `yearsAgo` omitted from on-this-day.
- Venue stub `name` is the authored `venue:` string.
- Search `playwright` becomes a descriptor string (no consumers yet; breaking is free).
