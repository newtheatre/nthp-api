---
type: task
status: done
---

# Seasons

Web doc 30 §1. Old site has `/seasons/{slug}/`; API has only a free-text `season` string.

## Output

- `GET /seasons/index.json` → `SeasonList[]` `{id, name, aliases[], showCount}`
- `GET /seasons/{id}.json` → `SeasonDetail = SeasonList & {shows: ShowList[]}`
- `seasonId` added to `ShowList`, `ShowDetail`, `ShowIndexItem` (14), `SearchDocument` (17)

## Do

- `seasons.py`: `SeasonDefinition(name, aliases)` list mirroring `roles.RoleDefinition`. Slug: downcase, keep `[a-z0-9 -]`, spaces→`-`, `---`→`-` (must match `_plugins/season.rb` `make_path`).
- Merges: `UNCUT`→`studio`, `Fringe`→`studio`, `Unscripted`→`creatives`.
- Raw values today: In House, StuFF, Fringe, Edinburgh, External, Postgrads, Lakeside, UNCUT, Online, Studio, Unscripted, Fundraiser, Creatives, Previews, IUDF, BedFest, `unknown`.
- `database.Show.season_id` indexed column set at load; grouping is a query.
- Unrecognised season → log error, still emit (don't drop the show). This list doubles as the season enum from plan Phase 2.
- Dumpers in `DUMPERS`, spec paths, tests.

## Open questions

- None. `unknown` is emitted as a record (`name: "Unknown"`) for reconciliation work.
