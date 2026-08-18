---
type: review
status: open
---

# nthp-api Completeness vs the Ruby/Jekyll Site Builder

*Assessed 2026-08-18 against the field specs in `history-project/_data/defs/`
and actual dump output. Companion to [02-Project review](02-Project%20review.md).*

nthp-api replaces the Jekyll static site builder in the content repo. This doc
tracks which parts of the content spec make it through to the JSON API, which
are ingested-then-dropped, and which are silently ignored.

Two failure modes to distinguish:

- **Silently ignored at ingest** — the pydantic models default to
  `extra="ignore"`, so any frontmatter field not modelled is dropped without
  warning. Content editors get no signal their data goes nowhere.
- **Ingested but never output** — the field is parsed and stored in the
  `data` JSON blob, but no dumper/schema emits it.

## Shows (`defs/show.yaml`)

| Field | Status |
|---|---|
| title, playwright, devised, improvised, adaptor, translator, student_written, company, period, season, season_sort, venue, date_start/end, cast, crew, cast/crew_incomplete, cast/crew_note, prod_shots, assets, trivia, canonical | ✅ Ingested and output |
| company_sort | ⚠️ Ingested, not output (company grouping lost) |
| **links** | ⚠️ **Ingested, not output** — show reviews/news (with publisher, rating, quote) are absent from `ShowDetail`. A whole content category (press reviews) missing from the API |
| playwright_alias | ❌ Silently ignored — student playwright crew attribution lost |
| playwright_false | ❌ Silently ignored — playwright wrongly kept in/out of crew list |
| venue_sort | ❌ Silently ignored — venue grouping (e.g. Edinburgh "C venues") lost |
| tour | ❌ Silently ignored (`# tour TODO` in models.py) |
| Generated: playwright_type/formatted | ✅ Structured equivalent (`PlaywrightShow.type`/`descriptor`) |
| Generated: excerpt | ➖ Replaced by `plaintext` in search documents; no per-show excerpt |
| Generated: seq_index/next/previous | ❌ No show-sequence navigation in API |
| Generated: redirect_from | ❌ Old-URL redirect data not exposed (client can't honour legacy URLs) |

## People (`defs/person.yaml`)

| Field | Status |
|---|---|
| title, id, submitted, headshot, graduated (incl. estimation) | ✅ |
| **links, news** | ⚠️ **Ingested, not output** — external profiles and news stories absent from `PersonDetail` |
| **award** | ⚠️ **Ingested, not output** — Fellowship/Commendation lost; also means no `fellows`/`commendations` lists on year pages (the Ruby site generates both) |
| course | ❌ Silently ignored (`TODO` in models.py — mixed string/list in content) |
| careers | ❌ Silently ignored (`TODO`) — alumni career data lost |
| gender | ➖ Deprecated in spec, correctly dropped |
| Generated: student, decade, has_bio, shows_count | ➖ Derivable client-side / partially present (`has_bio` in `PersonList`) |

## Venues (`defs/venue.yaml`)

| Field | Status |
|---|---|
| title, built, location, city, sort, shows, show_count | ✅ |
| **images** | ⚠️ Ingested, not output — `VenueDetail.assets` exists in the schema but `get_venue_detail` never populates it; venue photos absent |
| links | ⚠️ Ingested, not output |
| city_sort | ❌ Not generated (archive-page city grouping) |

## Committees, years, trivia, history

- Committees (`defs/committee.yaml`): ✅ fully covered via `YearDetail.committee` and role endpoints.
- Years (`defs/year.yaml`): core generated fields ✅. Missing vs Ruby: `fellows`, `commendations` (blocked on `award` above); key events only appear in the global `history/index.json` (records carry `year_id` so a client *can* map them onto year pages).
- Trivia (`defs/trivia-list.yaml`): ✅ fully covered, richer than Ruby (per-person trivia endpoints).
- Key events (`defs/key-events.yaml`): year/academic_year/title/description ✅; `image` (href + alt) ❌ silently ignored.

## Link list (`defs/link-list.yaml`)

The `Link` model ingests the full spec (type, href, username, snapshot, title,
date, publisher, rating, quote, note) — but **no output schema anywhere emits a
link**. All link-list content is currently dead weight. `href_snapshot`
generation (archive.is URL) would also need reimplementing when links are
output.

## Role definitions (`_data/roles.yaml`)

The Ruby site groups crew by `_data/roles.yaml`: **31 roles** with aliases and
icons. `nthp_build/roles.py` hardcodes **13 crew roles** (fewer aliases, no
icons) and 2 committee roles (President, Treasurer). Consequences:

- Crew-role browse pages exist for fewer than half the defined roles.
- Alias divergence: roles.yaml maps e.g. Author/Writer/Adaptor → Playwright;
  roles.py has no Playwright role at all.
- Consider reading roles.yaml from the content repo instead of hardcoding, so
  role curation stays with content editors.

## Other `_data` files not exposed

`careers.yaml`, `link-types.yaml`, `periods.yaml`, `seats.yaml` are consumed by
the Ruby site but have no API equivalent. They matter only once careers/links
are output (above); `seats.yaml` (seat sponsorship) may be out of scope —
confirm intentionally dropped.

## Summary of real gaps, roughly prioritised

1. **Links are ingested everywhere and output nowhere** — press reviews on
   shows, alumni profiles/news on people, venue websites. Largest single gap.
2. **award → fellows/commendations** — lost feature with social value.
3. **playwright_alias / playwright_false** — silently produce *wrong* crew
   lists, not just missing data.
4. **careers / course** — known TODOs, alumni data dropped.
5. **Venue images** — schema field exists, never populated.
6. **Role definitions** — hardcoded subset of roles.yaml.
7. redirect_from / seq navigation / venue_sort / company_sort / key-event
   images — smaller, decide deliberately whether the API's consumer needs them.

A cheap guard for the future: set `extra="forbid"` (or a warning hook) on the
ingest models so newly-invented frontmatter fields fail loudly instead of
silently vanishing — consistent with the "fail loudly" recommendation in the
main review.
