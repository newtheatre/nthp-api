---
type: task
status: open
---

# People index

A single index page for all people, enough for consumer list views without
fetching 3,365 per-person files. Consumer needs at minimum: name/title,
image id, graduated.

Today `dist/people/` holds only per-person detail files; there is no index.
The dump knows two kinds of people: **real** (have a bio document; get
`headshot`, `graduated`, `content`) and **virtual** (credited in show/committee
roles but no document; id and name only). Both get detail pages, so both
belong in the index — `hasBio` tells them apart (and is what list views need
to decide whether a person page is worth linking prominently).

## Proposed shape

`people/index.json`, a JSON array sorted by `id`:

```json
[
  {
    "id": "aaron_tej",
    "title": "Aaron Tej",
    "headshot": "people/aaron_tej.jpg",
    "graduated": {"year": 2016, "estimated": false},
    "hasBio": true
  },
  {
    "id": "some_actor",
    "title": "Some Actor",
    "hasBio": false
  }
]
```

- `id` — needed to link to `people/{id}`.
- `title` — display name, matching `PersonDetail.title`.
- `headshot` — same field name and value as `PersonDetail.headshot`, omitted
  when absent. The consumer called this "imageId"; keeping the API's existing
  name for consistency — it is the same value the detail page carries.
- `graduated` — compact `{year, estimated}` rather than the detail page's
  full `PersonGraduated` (`yearTitle`/`yearDecade`/`yearId`/`estimated`).
  Rationale: ×3,365 entries the full object is mostly derivable padding
  (`yearId`/`yearDecade` are functions of the year); a list view wants "2016"
  and perhaps an "estimated" marker. Omitted when unknown.
- `hasBio` — real vs virtual person.
- Nulls omitted (`exclude_none`), matching the existing response style.

Not included, deliberately: role counts, committee summary, `isPerson`
(constant true for everything this index lists), `content` snippets. Any of
these can be added later; the index is regenerated every build so the shape
is not locked in.

### Size

~3,365 entries × ~100–140 bytes ≈ 400–500 KB raw, ~60–90 KB gzipped —
acceptable for a single fetch backing search/browse list views. The fat
version with full `PersonGraduated` adds roughly 40% for no extra list-view
information, which is why the compact form is proposed.

## Implementation

- New schema: `PersonIndexItem` + collection in `schema.py` (near
  `PersonList`, which stays as-is for role listings), plus a compact
  `PersonIndexGraduated {year: int, estimated: bool}` — or reuse
  `PersonGraduated.from_year` input data before expansion.
- New dumper `dump_people_index` in `dumper.py`, registered alongside the
  existing people dumpers: query `database.Person` for real people (title,
  headshot, graduated fields) and `people.get_people_from_roles(excluded_ids=…)`
  for virtual ones — the same split `dump_real_people` / `dump_virtual_people`
  use, so the index provably covers exactly the pages that exist.
- Sort by `id` before writing (byte-reproducible builds, per doc 07 work).
- Write to `people/index.json` via the existing `make_out_path` helper.
- OpenAPI: add the response model to the spec with path `people/index`.

## Tests

- Index exists after dump; entry count equals real + virtual people count
  (i.e. the number of `people/*.json` detail files minus none — every detail
  page has an index entry and vice versa).
- A known real person has `title`, `headshot`, `graduated`, `hasBio: true`;
  a known virtual person has `hasBio: false` and no headshot.
- Sorted by `id`.
- Spec test (`test_spec.py`) picks up the new model.

## Open questions

1. Field name: keep `headshot` (consistent with `PersonDetail`) or rename to
   `imageId` across the API? Proposal: keep `headshot`.
2. Graduated: compact `{year, estimated}` as proposed, or full
   `PersonGraduated` for consistency with the detail page at ~40% more bytes?
3. Include virtual people (proposed: yes, with `hasBio: false`), or real
   people only?
