---
type: task
status: done
---

# Year identifiers

Web doc 30 §10. Breaking change, done now while there are no consumers.

## Output

- All year ids emit `YYYY-YY` (`2024-25`): `YearList.id`, `YearDetail.id`, `Show.id` (`2024-25/macbeth`), every `yearId`, people `yearIds`, committee references, history key events `year_id`, search documents.
- `YearList`/`YearDetail` gain `startYear: number`.
- File paths follow ids: `dist/years/2024-25.json`, `dist/shows/2024-25/macbeth.json`.

## Do

- Load side keeps parsing `YY_YY` source dirs (`get_year_from_year_id`, Y2K split at 40 — still needs the 2039 fix from plan Phase 4, or derive the century from the folder's neighbours). Convert at the boundary once: store `year` int in the DB and derive the public id in one function `get_public_year_id(year)`.
- Grep for every place that emits or composes a year id; `rg '_\d\d' tests/` for fixtures.
- No `legacyId`, no duplicate dump.
- Content-repo directory rename is a separate later step.

Do this **before** 14/17/18 so new `yearId` fields are written once.
