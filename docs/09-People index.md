---
type: task
status: done
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
    "graduated": {
      "yearTitle": "2016", "yearDecade": 2010, "yearId": "15_16",
      "estimated": false
    },
    "submitted": "2016-05",
    "showRoleCount": 12,
    "committeeRoleCount": 2,
    "hasBio": true
  },
  {
    "id": "some_actor",
    "title": "Some Actor",
    "showRoleCount": 1,
    "committeeRoleCount": 0,
    "hasBio": false
  }
]
```

- `id` — needed to link to `people/{id}`.
- `title` — display name, matching `PersonDetail.title`.
- `headshot` — same field name and value as `PersonDetail.headshot`, omitted
  when absent. (Considered renaming to the consumer's "imageId"; keeping the
  API's existing name — it is the same value the detail page carries.)
- `graduated` — the full `PersonGraduated` object, identical to the detail
  page (consistency won over the ~40% size saving of a compact form).
  Omitted when unknown.
- `submitted` — as on `PersonDetail`: fuzzy date string, or boolean, omitted
  when null.
- `showRoleCount` / `committeeRoleCount` — plain ints, always present
  (0 allowed: a real person may have a bio but no credited roles).
- `hasBio` — real vs virtual person.
- Nulls omitted (`exclude_none`), matching the existing response style.

Not included, deliberately: `isPerson` (constant true for everything this
index lists), `content` snippets. The index is regenerated every build so the
shape is not locked in.

### Size

~3,365 entries × ~180–250 bytes ≈ 700–850 KB raw, roughly 80–120 KB gzipped —
still a single acceptable fetch for list views.

## Implementation

- New schema: `PersonIndexItem` + collection in `schema.py` (near
  `PersonList`, which stays as-is for role listings), reusing `PersonGraduated`
  as-is.
- New dumper `dump_people_index` in `dumper.py`, registered alongside the
  existing people dumpers: query `database.Person` for real people (title,
  headshot, graduated, submitted fields) and
  `people.get_people_from_roles(excluded_ids=…)` for virtual ones — the same
  split `dump_real_people` / `dump_virtual_people` use, so the index provably
  covers exactly the pages that exist.
- Role counts: aggregate over the `PersonRole` table grouped by person id and
  role kind (show vs committee), one query for all people, joined onto the
  index entries in Python — not per-person queries (the collaborators dumper
  shows where that leads).
- Sort by `id` before writing (byte-reproducible builds, per doc 07 work).
- Write to `people/index.json` via the existing `make_out_path` helper.
- OpenAPI: add the response model to the spec with path `people/index`.

## Tests

- Index exists after dump; entry count equals real + virtual people count
  (i.e. the number of `people/*.json` detail files minus none — every detail
  page has an index entry and vice versa).
- A known real person has `title`, `headshot`, `graduated`, `submitted`,
  role counts, `hasBio: true`; a known virtual person has `hasBio: false`,
  no headshot, and correct role counts.
- Role counts on a sampled person match the lengths of `show_roles` /
  `committee_roles` on their detail page.
- Sorted by `id`.
- Spec test (`test_spec.py`) picks up the new model.

## Decisions

1. Keep `headshot` as the field name (not `imageId`) — consistent with
   `PersonDetail`, same value.
2. Full `PersonGraduated`, identical to the detail page.
3. Virtual people included, `hasBio: false`.
4. Also carry `submitted` and `showRoleCount` / `committeeRoleCount`.

## Outcome

Done. 3,480 entries, 656 KB raw / 65 KB gzipped — inside the estimate, and the
gzipped figure is what consumers actually fetch. `dump_people_index` takes
0.84 s.

Every entry was checked against its own detail page after a real build: all
3,480 match on `title`, `headshot`, `graduated`, `submitted` and both counts,
and the index covers exactly the set of detail pages, sorted and unique.

### The two counts are not counted the same way

`showRoleCount` counts **distinct shows** while `committeeRoleCount` counts
**role rows**, because that is what the detail page does:
`get_person_show_roles` groups a person's roles by show (two credits on one
show is one entry), whereas `get_person_committee_roles` emits one entry per
row (holding President twice is two entries). Counting rows for both would
have inflated `showRoleCount` for **496 of 3,632 people** — Zoe Smith would
have read 103 instead of 78. The helpers in `people.py` carry this in their
docstrings, and a test pins each behaviour.

### Deviations from the plan

- Real people's fields come from `models.Person(**json.loads(inst.data))`, not
  from `database.Person` columns as the plan suggested. `submitted` is not a
  column at all, and `graduated` on a detail page is `get_graduation()`, which
  *estimates* from credits when the document has no year — 2,941 of 3,470
  graduation values are estimated, virtual people included. Reading the columns
  would have silently disagreed with the detail pages.
- `PersonIndexItem` sits next to `PersonDetail` rather than `PersonList`, as it
  refers to `PersonGraduated`, which is defined below `PersonList`.
- Role counts take two aggregate queries rather than one grouped by role kind:
  a person who both acted in and crewed the same show must count that show
  once, which a per-kind grouping cannot express.
