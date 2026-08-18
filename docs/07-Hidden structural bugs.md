---
type: task
status: done
---

# Hidden structural bugs

Implements §1 of [02-Project review](02-Project%20review.md). Findings 1.1,
1.2, 1.4, 1.5. Finding 1.3 (validation failures don't fail the build) is
**deliberately deferred**: this is not yet the production build, so staying
conservative — tolerate bad documents rather than turning builds red. Leave it
open in the review.

One commit per finding.

## 1.1 Fix `asset_title` / `asset_page` kwargs

Decision: fix the kwargs (not drop the columns) — populate them correctly.

- `nthp_api/nthp_build/assets.py:84`: pass `asset_title=` / `asset_page=` to
  `database.Asset.create()` instead of `title=` / `page=`, which peewee
  silently discards.
- Verify against a real build: previously 1,955 asset rows with 0 titles;
  after the fix rows with a title in source should populate (compare with
  `asset_category`, correctly named and populated on 1,596).
- Add/extend a test asserting a loaded asset row carries title and page.
- API output should be byte-identical (show pages read the `Show.assets` JSON
  blob, not these columns) — confirm with a before/after `dist/` diff on a
  sample.

## 1.2 Academic-year-aware `year_end`

Decision: keep the wall clock but make it academic-year-aware — the theatre is
university-based, years run September–August.

```python
year_end = now.year + 1 if now.month >= 9 else now.year
```

- `nthp_api/nthp_build/config.py:13`. Verify the exclusive/inclusive semantics
  at the point of use (`dumper.py:122`) so that from 1 September a show filed
  under the new academic year (e.g. `26_27` in September 2026) gets its year
  page and `years/index` entry.
- Test both sides of the boundary (August vs September) with a frozen clock;
  avoid embedding wall-clock reads in the logic under test (make the function
  take `today`-like input, default `date.today()`).

## 1.4 Pin the `fork` start method

Decision: pin `fork`, keep the multiprocessing pool (and its speed).

- Call `multiprocessing.set_start_method("fork")` (or use
  `multiprocessing.get_context("fork")` for the `Process` creation, which
  avoids global state) in `dumper.dump_all()` before spawning children.
- This is what keeps `nthp build` (`DB_URI=:memory:`) working when the Python
  pin moves past 3.13 (Linux default becomes `forkserver`).
- Note: `fork` is Linux/macOS-only; that's acceptable — CI and dev are Linux.

## 1.5 Sort `find_documents` output

- `documents.find_documents()`: sort the `rglob` results (by path) so document
  ordering — and therefore JSON array ordering in outputs — is deterministic
  across filesystems and runs, making builds byte-reproducible.
- Confirm with two consecutive builds diffing clean.

## Tests / verification

- `uv run pytest` after each item.
- Full pipeline `./nthp load content && ./nthp dump` at the end; diff `dist/`
  against a pre-change build — only expected differences (none for 1.1/1.4;
  possible array reordering for 1.5; year pages only if run in Sept–Dec).

## Decisions

1. 1.1: populate columns, don't drop them.
2. 1.2: academic-year wall clock (`month >= 9` → `year + 1`), not
   data-derived.
3. 1.3: skipped for now — pre-production, stay tolerant. Review stays open on
   this point.
4. 1.4: pin `fork`, keep the pool.

## Outcome

Done. One commit per finding; 1.3 left open as agreed.

- **1.1**: 698 asset rows now carry a title and 89 a page, from 0 of 1,913
  before. Output is unchanged — verified by building `dist/` with and without
  the fix back to back, which differed only in `buildTime`.
- **1.2**: `get_current_year_end(today)` lives in `config.py`, not `years.py`,
  because `years` imports `documents` which imports `config` — putting it in
  `years` would have been a cycle. `year_end` is now a `default_factory`.
  Today (August 2026) it still returns 2026, so no output change until
  September.
- **1.4**: `parallel.MP_CONTEXT = multiprocessing.get_context("fork")` supplies
  `Process`, `Queue` and the `Manager`, so no global state is touched.
  Verified by running the in-memory build under
  `multiprocessing.set_start_method("forkserver")` — the Python 3.14 default:
  it fails with `no such table: personrole` without the fix and completes
  normally with it.
- **1.5**: sorting `find_documents` alone did **not** make builds reproducible.
  Two further sources of ordering churn had to go, both sets iterated under
  hash randomisation, plus one list assembled concurrently:
  - `dump_crew_roles` emitted `list(role.aliases)` from a `set`;
  - `get_show_people_names` returned a `set`, feeding `search/documents.json`;
  - the search document list is appended to by parallel dumpers, so it now
    sorts by `(type, id)` before it is written.

  Two consecutive full builds now differ only in `buildTime`.

### Noticed in passing

`content/_people/nick_gill.md` fails validation on `submitted: 04/01/2017`, so
a Fellowship holder is silently absent from the API — his headshot and bio are
missing and every show he crewed reports `hasBio: false`. Exactly the failure
mode finding 1.3 describes, now with a name attached. Worth weighing when 1.3
is picked up.
