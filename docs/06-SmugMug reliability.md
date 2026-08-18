---
type: task
status: open
---

# SmugMug step reliability

Implements "SmugMug step: the reliability weak point" from
[02-Project review](02-Project%20review.md) §2, plus the related seed-file
fallback from §3.1. The `smug` step is the only part of the build that talks to
an external API at build time; every finding below is a way for it to take the
whole unattended build down, or to silently degrade.

Current shape: `nthp smug` (`nthp_build/smugmug.py`) gathers one
`update_album` task per SmugMug album asset. `smugmugger/smugmug.py`
serves each album from the `nthp.smug.db` cache if present, else fetches via
`smugmugger/client.py` and caches. CI (`build.yml`) restores `nthp.smug.db`
from an Actions cache, seeding a cold cache from
`nthp-seed.s3.eu-west-2.amazonaws.com` via `wget -nc`.

## 1. One bad album fails the whole step

`nthp_build/smugmug.py:32` uses bare `asyncio.gather` — the first
`SmugMugNotFound` (deleted album) or `SmugMugApiError` cancels nothing but
propagates, failing the step with all other results discarded.

- Gather with `return_exceptions=True` (or per-task try/except in
  `update_album`).
- `SmugMugNotFound` → log a warning, skip the album, continue. The album stays
  in the output with whatever `asset_smugmug_data` it already has.
- Other errors → continue the sweep, then fail the step at the end with a
  summary (`N albums failed`) so partial data is cached but the failure is
  still loud. Silent partial success is the failure mode §3.3 warns about.

## 2. Retry only covers transport errors

`smugmugger/client.py:52` `_get_with_retry` retries `httpx.TimeoutException` /
`TransportError` only. HTTP 429/5xx come back as a response, pass the retry
loop, and raise `SmugMugApiError` immediately (`client.py:92`).

- Retry retryable statuses: 429, 500, 502, 503, 504, reusing the existing
  backoff; honour `Retry-After` on 429 if present.
- 404 stays immediate (`SmugMugNotFound` — retrying won't help).
- Existing settings `smugmug_retry_attempts` / `smugmug_retry_backoff_seconds`
  apply unchanged.

## 3. Actions cache never re-saves

`build.yml:25` uses `actions/cache@v4` with fixed key `smugmug-1`.
`actions/cache` skips the save step on an exact-key hit, so the cache is frozen
at whatever it held when first saved — every album added since is re-fetched
from the API on every build, and that set only grows.

```yaml
- uses: actions/cache@v4
  with:
    path: nthp.smug.db
    key: smugmug-${{ github.run_id }}
    restore-keys: |
      smugmug-
```

Per-run key never exactly hits, so the updated db is saved after every run;
`restore-keys` restores the most recent previous one. The `wget -nc` seed step
already tolerates the file existing, so ordering is unchanged. Note Actions
evicts caches unused for 7 days — the seed download remains the cold-start
path, which is fine.

## 4. Cache never invalidates

`smugmugger/smugmug.py:47` returns cached data unconditionally.
`last_updated` (SmugMug's `ImagesLastUpdated`) and `last_fetched` are stored
but never read — an album updated on SmugMug never refreshes without manually
deleting its row.

Checking staleness properly costs one `get_album` metadata request per album
per build (compare live `ImagesLastUpdated` to cached `last_updated`), which
reintroduces the API as a per-build dependency for every album — against the
grain of items 1–3. Cheaper option: TTL on `last_fetched` (e.g. refetch after
90 days), which spreads refreshes and needs no extra requests. Or accept
never-invalidate as intentional and document it in the README, keeping manual
row deletion as the escape hatch.

## 5. Build should survive SmugMug being down entirely

§3.1: the step already has an off switch — `smugmug_fetch`
(`smugmugger/smugmug.py:49`) returns an empty collection for uncached albums
without touching the API. Verified `SMUGMUG_FETCH=false ./nthp build content`
runs the full pipeline to completion with no API key; it just isn't wired into
CI. And if the seed bucket dies, a cold-cache CI build fails at the `wget -nc`
step before that setting matters.

- Make the wget step non-fatal (`|| true` with a warning, or an `if:` guard),
  so a missing seed degrades to "no cached data" rather than a dead pipeline.
- Optionally set `SMUGMUG_FETCH=false` as the fallback when the API key secret
  is absent, so forks/rebuilds still produce an API without images.

## Order of work

1. Status-code retries in `client.py` (2) — smallest, purely internal.
2. Error tolerance in the gather (1), with tests using stubbed
   failures.
3. CI cache key + seed fallback (3, 5) — `build.yml` only.
4. Decide and implement (or document) invalidation policy (4).

## Tests

`smugmugger/client.py` retry behaviour is testable with `httpx.MockTransport`
(or respx): 429-then-200 succeeds, 404 raises `SmugMugNotFound` immediately,
5xx exhausting attempts raises. Gather tolerance: stub `get_album_images` to
raise for one album, assert the others still save and the step reports the
failure. CI changes are verify-by-run.

## Decisions

1. Non-404 fetch failures: fail the step after the sweep (recommended, keeps
   failures loud) or warn and continue?
2. Invalidation policy: TTL on `last_fetched`, per-build `ImagesLastUpdated`
   check, or document never-invalidate as intentional?
3. Is `SMUGMUG_FETCH=false`-on-missing-key wanted in CI, or should a missing
   key stay fatal?
