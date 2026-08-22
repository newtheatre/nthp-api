---
type: task
status: done
---

# Image dimensions

Web doc 30 §7. Every SmugMug asset the API emits must carry `width`, `height` (and `date` where known) so the site can set intrinsic dimensions.

## Output

`schema.Asset` gains `width?: number, height?: number, date?: string`. Null + logged where SmugMug cannot answer — never silently absent.

## Do

- Album images: data already in `database.Asset.asset_smugmug_data` (`OriginalWidth/Height`, `Date`), discarded by `smugmug_asset_to_asset`. Free win — do first.
- Posters, headshots, venue photos: bare keys from frontmatter, never fetched. Need `GET /api/v2/image/{key}!sizedetails` per key (~1500) at load with a persistent cache, as old `smugmug_image.rb` did.
- Cache: extend the `nthp.smug.db` seed/cache rather than a new store; fix the Actions cache key that never updates (06).
- Depends on [06 SmugMug reliability](06-SmugMug%20reliability.md): retries on 429/5xx before adding 1500 calls.
- Alt text: not in content, out of scope.

Decision: live calls with persistent cache; first run slow, accepted.

## Done

`GET /api/v2/image/{key}` carries `OriginalWidth`, `OriginalHeight` and `Date`
in one request, so `!sizedetails` is only a fallback. That endpoint 301s from
the bare key to its serial-suffixed URI, so the client follows redirects
(a2bf036). Live-checked against three 2024/25 posters.
