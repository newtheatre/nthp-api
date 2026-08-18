---
type: task
status: open
---

# Fuzzy date field

Implements "Too strict: dates" from [04-Strictness review](04-Strictness%20review.md).
An archive holds partial dates; the schema should model precision, not reject it.
Clears 5 of the 6 current validation failures with the data as-is.

## The type

`FuzzyDate` — frozen dataclass in `nthp_api/nthp_build/fields.py`, wired into
pydantic via `__get_pydantic_core_schema__` so it works as a field type on both
ingest models and output schema.

```python
@dataclass(frozen=True)
class FuzzyDate:
    year: int
    month: int | None = None   # month set ⇒ never day without month
    day: int | None = None
```

### Accepts (validation)

| Input | Source | Result |
|---|---|---|
| `datetime.date` | YAML parses `2001-06-14` | day precision |
| `int` in year range | YAML parses bare `2007` | year precision |
| `str` `YYYY` | quoted year | year precision |
| `str` `YYYY-MM` | YAML leaves `2001-06` as str | month precision |
| `str` `YYYY-MM-DD` | quoted full date | day precision |
| `FuzzyDate` | revalidation on JSON round-trip | itself |

Rejects: `bool` (checked before `int` — `bool` is an `int` subclass, and
`Person.submitted` is `FuzzyDate | bool`), `datetime.datetime` (a time
component means malformed source — fix the document, keep the source clean),
years outside the archive range, `2007-13`, `04/01/2017`, and anything else.
Month/day validated by constructing `datetime.date(year, month, day or 1)` —
real calendar dates only.

Year range: clamp to the archive's plausible span, module constants
`MIN_YEAR = 1900`, `MAX_YEAR = 2100` (theatre founded 1920; generous headroom
either side). Applies to all input paths, including the year of a full
`datetime.date`.

### Serialises (output)

`str(FuzzyDate)` → ISO 8601 reduced precision: `"2001"`, `"2001-06"`,
`"2001-06-14"`. Used for pydantic JSON serialisation and the DB columns.
Consumers read precision from string length. JSON schema:
`{"type": "string", "pattern": "^\\d{4}(-\\d{2}(-\\d{2})?)?$"}` — the OpenAPI
spec output changes from `format: date` accordingly.

### Behaviour

- Ordering (`__lt__` etc.): compare the ISO strings. Lexicographic order on
  reduced ISO equals order-by-earliest-date with lower precision sorting first
  (`"2001" < "2001-06" < "2001-06-14"`), which is what show listings want.
- Helpers for later date-sanity checks (doc 04 item 5): `earliest() -> date`
  (first day of period), `latest() -> date` (last day). Optional in the first
  cut.
- Hashable/frozen — models use `ConfigDict(frozen=True)`.

## Field changes

Ingest, `models.py`:

- `Show.date_start`, `Show.date_end` (`models.py:140`)
- `Link.date` (`models.py:28`) — covers show links, person links, person news
- `Trivia.submitted` (`models.py:109`)
- `Person.submitted` (`models.py:174`) — becomes `FuzzyDate | bool | None`

Output, `schema.py` (breaking API change, accepted — camelCase fields switch
from `format: date` to fuzzy string while not yet the production build):

- `ShowDetail.date_start/date_end` (`schema.py:113`)
- `ShowList.date_start/date_end` (`schema.py:136`)
- `PlaywrightShowListItem.date_start/date_end` (`schema.py:144`)
- `PersonDetail.submitted` (`schema.py:280`)
- `BaseTrivia.submitted` (`schema.py:309`)

Not changing: `Venue.built` (plain int year is fine), `HistoryRecord.year`
(already `PermissiveStr`).

## Storage and sorting

- `database.py`: `Show.date_start/date_end` (`database.py:52`) and
  `Trivia.submitted` (`database.py:100`) change `DateField` → `CharField`,
  holding the reduced ISO string. DB is dropped and rebuilt every run
  (`database.py:131`) — no migration.
- Sorting: SQLite text sort on reduced ISO strings is already
  earliest-date order, so the review's "store first day alongside" column is
  unnecessary — one text column does both jobs. `get_show_query`
  (`shows.py:8`) and the `date_start` index are unchanged.
- `loader.py:49` / `trivia.py:25` pass `str(value)` (or `None`) when writing
  rows; `shows.py:141`/`trivia.py:42` feed the string straight back into
  schema models, which revalidate it as `FuzzyDate`.
- JSON round-trip: `data.model_dump_json()` stores `"2001-06"`;
  `models.Show(**json.loads(...))` (`shows.py:132`) revalidates via the str
  path. Must be lossless.

## Tests

`tests/test_nthp_build/` — new `test_fields.py` (or extend `test_models.py`):

- Each accepted input form → expected precision and str output
- Rejections: bool, datetime, out-of-range years (`1899`, `2101`), `2007-13`,
  `2001-06-31`, `04/01/2017`
- Ordering: mixed-precision sort matches expected chronology
- Round-trip: model → JSON → model equality, for a Show with `YYYY-MM` date
- `Person.submitted: true` still validates as bool
- Update `test_spec.py` expectations for the schema change

## Order of work

1. `FuzzyDate` in `fields.py` + unit tests
2. Swap ingest model fields; confirm the 5 target documents now validate
   against the live content repo
3. Swap output schema fields + DB columns + loader/dumper call sites
4. Regenerate/verify OpenAPI spec, update tests

## Decisions

1. `datetime.datetime` input: reject — keep the source clean.
2. Year bounds: clamp to archive range (1900–2100).
3. Output API shape: break it now — fuzzy strings replace `format: date`.
