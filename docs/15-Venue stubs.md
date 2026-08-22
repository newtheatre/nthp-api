---
type: task
status: todo
---

# Venue stubs

Web doc 30 §4; 03 `venue_sort`, venue `images`. 36 filed venues, 70 distinct ids referenced by shows → 34 show-page venue links 404.

## Output

- `VenueList`/`VenueDetail` gain `hasRecord: boolean` and `sentinel: boolean`.
- Every referenced venue id gets a detail file and an index entry. Stubs: `id, name, showCount, hasRecord: false, shows[]`; no built/location/city/content.
- Sentinels `unknown` → "Venue unknown", `youtube` → "Online — YouTube", `sentinel: true`.
- `venueSort` output on `VenueList`/`VenueDetail` (grouping e.g. Edinburgh "C venues").
- `VenueDetail.assets` populated from `images` (declared, never filled). Dimensions via 20.

## Do

- Stub name = the authored `venue:` string (shows write `venue: Portland Studio`, id is slugified). Where authored spellings differ for one id, take the most common and log.
- Highest-volume missing: unknown 28, youtube 20, portland-studio 8, zoo-monkeyhouse 6, studio-live 5, the-zoo 4, c-soco 4, royal-terrace-greenside 4, infirmary-street-greenside 4.
- No `location` required — site drops maps.
- Existing "phantom venue" lint idea (plan Phase 2) becomes informational: stubs are expected, not errors.
