---
type: task
status: todo
---

# Shows index and sequence

Web doc 30 §3 and §11 (prev/next, missingFields, ignore_missing); 03 `company_sort`, `seq_*`.

## Output

- `GET /shows/index.json` → `ShowIndexItem[]`: `id, title, yearId, year, season, seasonId, venue?{id,name}, dateStart?, dateEnd?, primaryImage?, playwrightDescriptor?`. Lighter than `ShowList`; ~1054 items. Order = `shows.get_show_query()` (season_sort, date_start).
- `ShowDetail` gains:
  - `previous?` / `next?` `{id, title, primaryImage?}` across the whole corpus in the same order
  - `missingFields: string[]` — facts only; threshold (≥4, `show_low_crew: 5`) stays in the site. Values verbatim from `_plugins/show.rb` `missing_majority`: `date_start`, `poster` (no primary image), `excerpt` (no content), `cast` *or* `cast_incomplete`, `crew` *or* `crew_short` (≤ `show_low_crew`), `playwright` (type unknown), `venue`.
  - `tour` (03: silently ignored) — ingest and output
  - `ignoreMissing: boolean`, `ignoreMissingInSeasons: boolean` (new ingest fields — currently silently dropped)
  - `companySort?` (ingested, never output)

## Do

- Index dumper reuses the canonical query; prev/next computed once over the ordered list, not per-show queries.
- `ShowIndexItem.venue.name` requires 15 (stub names) so every venue resolves.
- Spec, tests.

Depends on 19 for `yearId` form.
