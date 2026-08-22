---
type: task
status: done
---

# Shows index and sequence

Web doc 30 §3 and §11 (prev/next, missingFields, ignore_missing); 03 `company_sort`, `seq_*`.

## Output

- `GET /shows/index.json` → `ShowIndexItem[]`: `id, title, yearId, year, season, seasonId, venue?{id,name}, dateStart?, dateEnd?, primaryImage?, playwrightDescriptor?`. Lighter than `ShowList`; ~1054 items. Order = `shows.get_show_query()` (season_sort, date_start).
- `ShowDetail` gains:
  - `previous?` / `next?` `{id, title, primaryImage?}` across the whole corpus in the same order
  - `missingFields: string[]` — facts only; threshold (≥4, `show_low_crew: 5`) stays in the site. Values verbatim from `_plugins/show.rb` `missing_majority`: `date_start`, `poster` (no primary image), `excerpt` (no content), `cast` _or_ `cast_incomplete`, `crew` _or_ `crew_short` (≤ `show_low_crew`), `playwright` (type unknown), `venue`.
  - `tour` (03: silently ignored) — ingest and output
  - `ignoreMissing: boolean`, `ignoreMissingInSeasons: boolean` (new ingest fields — currently silently dropped)
  - `companySort?` (ingested, never output)

## Do

- Index dumper reuses the canonical query; prev/next computed once over the ordered list, not per-show queries.
- `ShowIndexItem.venue.name` requires 15 (stub names) so every venue resolves.
- Spec, tests.

Depends on 19 for `yearId` form.

## As built

- Canonical order is year, `season_sort` (shows without one falling to the end of the year, as `_plugins/show.rb` `sort_shows` has them), `date_start`, then id.
- `playwright` is a missing field when the show has no authorship at all, as well as when it is authored `unknown`; the old site's `playwright_type` is `unknown` in both cases.
- `ignoreMissing` is the authored `ignore_missing` flag; `ignoreMissingInSeasons` comes from the `ignore_missing_in_season_ids` setting, mirroring `_config.yml`. The old site merged the two into one flag.
- `tour` entries carry `venue`, `date_start`, `date_end` and `note` (`notes` accepted as an alias); the authored `comment` is ingested but not output.
