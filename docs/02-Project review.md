---
type: review
status: open
---

# nthp-api Project Review

*Reviewed 2026-08-18, at commit `a45c94a` (post uv migration / dependency upgrade).*

The project converts the [history-project](https://github.com/newtheatre/history-project)
content repo into a static JSON API: content → sqlite → JSON files deployed to S3.

**Overall**: the architecture is right for the goal. A static dump has nothing to
serve and nothing to patch at runtime — the best possible shape for operating
through lack of maintenance. The risks are all at the edges: external services,
CI rot, and failures that don't fail the build.

Feature completeness against the Ruby/Jekyll builder this replaces is covered
separately in [03-Completeness review](03-Completeness%20review.md).

## 1. Hidden structural bugs

### 1.1 `asset_title` / `asset_page` are never written

`nthp_api/nthp_build/assets.py:84` passes `title=` / `page=` to
`database.Asset.create()`, but the model fields are `asset_title` /
`asset_page`. Peewee silently accepts unknown kwargs as instance attributes and
drops them on insert.

Verified against a real build: 1,955 asset rows, **0** with title or page,
while `asset_category` (passed with the correct name) is populated on 1,596.

Per the content spec (`history-project/_data/defs/assets.yaml`), `title` is
required alongside `filename` and displayed for videos/files, and `page` orders
assets within a type — so these are meaningful values, not vestigial. API
output is unaffected today only because show pages embed assets from the
`Show.assets` JSON blob (which retains title/page), not from the `Asset` table;
the table columns are write-only. **Fix the kwargs or drop the columns** —
leaving broken write-only columns invites a future dumper reading NULLs.

### 1.2 Current academic year missing from September to December

`nthp_api/nthp_build/config.py:13` sets `year_end = datetime.now().year`, used
as an *exclusive* bound in `dumper.py:122`. A show filed under `26_27` from
September 2026 gets a show page, but no year page and no `years/index` entry
until 1 January 2027.

**Fix**: derive the range from `max(Show.year)` in the database (also removes
the wall-clock dependency from the build), or use `now().year + 1`.

### 1.3 Validation failures do not fail the build

`loader.py:226` logs "N documents failed validation" and the process exits 0;
the deploy proceeds with those documents silently absent from the API
(6 documents today). Related:

- A YAML parse error in `_data/history.yaml` logs and returns — the history
  endpoint is simply missing.
- Duplicate person IDs (`load_person`) log an error and continue.

For an unattended pipeline this is the wrong default: content quietly vanishes
and nobody is told. **Minimum fix**: nonzero exit on any failure. **Better**:
an allowlist for the 6 known-bad legacy documents so new breakage fails loudly
while old breakage stays tolerated.

### 1.4 `nthp build` (in-memory db) depends on the `fork` start method

`dumper.dump_all()` runs the 15 dumpers as `multiprocessing.Process` children.
With `DB_URI=:memory:` (the `build` command) the children only see the loaded
data because Linux forks the parent's memory. Python 3.14 changed the Linux
default start method to `forkserver` — bumping the interpreter pin past 3.13
breaks `build` (children would see an empty database). A time-bomb rather than
a bug today.

**Fix**: call `multiprocessing.set_start_method("fork")` explicitly, or drop
the process pool entirely — the whole dump takes ~10 s and the parallelism
mainly buys back the 8.5 s collaborators dump.

### 1.5 Non-deterministic document ordering

`documents.find_documents()` uses `rglob`, whose ordering is
filesystem-dependent. JSON array ordering in some outputs can differ between
machines/runs. Sorting the results makes builds byte-reproducible and diffs
between deploys meaningful.

## 2. Faster / more reliable

### Speed: a non-issue

Full local pipeline is ~15 s. The one hotspot is `dump_collaborators` (8.5 s):
`get_person_collaborators` issues 2 queries per person × ~2,600 people. It
collapses into a single self-join with grouping if it ever matters. Not worth
optimising today; CI wall-time is dominated by checkout/setup.

### SmugMug step: the reliability weak point

- **No error tolerance**: `smugmug.py:32` uses a bare `asyncio.gather`; one
  deleted album (`SmugMugNotFound`) or one rate-limit response fails the whole
  step.
- **HTTP errors are not retried**: the retry/backoff in
  `smugmugger/client.py` covers transport errors and timeouts only — 429/5xx
  raise immediately. Retry on retryable statuses; treat 404 as "album gone,
  skip with a warning".
- **The Actions cache never updates**: `build.yml` uses `actions/cache` with
  the fixed key `smugmug-1`. `actions/cache` never re-saves on a hit, so every
  album fetched since the cache was first saved is re-fetched on every build,
  forever, and the set grows. Use a per-run key with a `restore-keys` prefix so
  the updated db is saved each run.
- **The cache never invalidates**: `get_album_images` returns cached data
  unconditionally, ignoring the `ImagesLastUpdated` value it stores. Updated
  albums never refresh without manual row deletion. Fine if intentional —
  document it if so.

### Smaller items

- Leftover pydantic v1 API calls: `dumper.py:51` (`obj.json(...)`) and
  `smugmug.py:21` (`.json(...)`). Deprecated; removed in pydantic v3. Two-line
  fix now, build-breaker later.
- `SiteStats.build_time` uses naive `datetime.now()` — emit UTC ISO 8601.

## 3. Operating unattended for years

Ranked by likelihood of being the thing that breaks it:

1. **External services.** SmugMug API and key; the seed file
   `nthp-seed.s3.eu-west-2.amazonaws.com/nthp.smug.db` (fetched with
   `wget -nc` — if that bucket dies, the first cold-cache build fails); S3
   deploy credentials. Mitigations: commit a fallback copy of the smug db or
   make `SMUGMUG_FETCH=false` the CI fallback so the API still builds (without
   fresh images) when SmugMug is unreachable.
2. **GitHub Actions rot.** `ubuntu-latest` churn, action major-version
   deprecations, the pinned `astral-sh/setup-uv@v6`. A monthly scheduled build
   (`on: schedule:`) is cheap insurance: you find out a build broke from age,
   not when someone edits content years later.
3. **Silent failure culture** (findings 1.2, 1.3). Unattended means nobody
   reads logs — every anomaly should be fatal or surfaced (badge/notification).
4. **Y2K39.** `years.py` maps two-digit years < 40 to 2000s: `40_41` becomes
   1940. Breaks in September 2039 — within a "runs for years" horizon.
5. **Dependency longevity** — low risk. peewee/click/markdown/pyyaml are
   geologically stable. `pytest-vcr` is unmaintained and `pydantic-collections`
   is a one-person shim; both are trivially replaceable (vcrpy directly; a
   pydantic `RootModel` list) next time they block an upgrade. `uv.lock` keeps
   builds reproducible regardless.

## Recommended actions

| Priority | Action | Effort |
|---|---|---|
| High | Fail the build on validation errors (with legacy allowlist) | Small |
| High | Add scheduled monthly CI build | Trivial |
| High | Fix `year_end` off-by-one (1.2) | Trivial |
| Medium | Fix `asset_title`/`asset_page` kwargs (1.1) | Trivial |
| Medium | SmugMug: retry on 429/5xx, tolerate 404, fix Actions cache key | Small |
| Medium | Replace deprecated `.json()` calls | Trivial |
| Low | Pin `fork` start method or drop multiprocessing (1.4) | Small |
| Low | Sort `find_documents` output (1.5) | Trivial |
| Low | Fix Y2K39 window before 2039 | Trivial |
