---
type: reference
---

# Project plan

nthp-api converts the [history-project](https://github.com/newtheatre/history-project) content repo into a static JSON API (content → sqlite → JSON on S3). It is to replace the Ruby/Jekyll static site builder in the content repo as the production build. It must then operate for years with minimal maintenance.

State (2026-08-18): tooling modernised (uv, Python 3.13, all deps current, ruff format). Three reviews done — docs 02–04. Not yet the production build.

## Phase 1 — Trustworthy builds

The build must fail loudly before anything else matters; unattended means nobody reads logs.

- Nonzero exit on validation failure, with a grandfathered-document allowlist that only shrinks (docs 02 §1.3, 04)
- Scheduled monthly CI build — catch rot from age, not from the next content edit (doc 02 §3)
- Fix `year_end` off-by-one: current academic year missing Sept–Dec (doc 02 §1.2)
- Fix `asset_title`/`asset_page` write-only columns (doc 02 §1.1)
- Replace deprecated pydantic `.json()` calls (doc 02 §2)
- Sort `find_documents` output for reproducible builds (doc 02 §1.5)

## Phase 2 — Strictness (doc 04)

- Fuzzy date type accepting `YYYY` / `YYYY-MM` / `YYYY-MM-DD`; output ISO reduced-precision strings. Clears 5 of 6 current validation failures
- `extra="forbid"` on ingest models — stop silently dropping unknown frontmatter
- `season`/`period` enums from the real value lists
- Date sanity checks (end ≥ start, within academic year of folder)
- `nthp lint` command: phantom venues, near-duplicate person ids, unmatched roles — reported in CI, never failing
- Source-repo fixups: `nick_gill.md` date, `spring`→`Spring`, `period: unknown`

## Phase 3 — Completeness (doc 03)

Parity with the Ruby builder where its features still matter:

- Output links everywhere they are ingested: show reviews, person profiles/news, venue websites — the largest gap
- `award` → person output + year fellows/commendations lists
- `playwright_alias` / `playwright_false` — currently produce wrong crew lists
- Adopt `roles.yaml` from the content repo (31 roles) over the hardcoded 13
- `careers`/`course`, venue images, then the long tail (doc 03 §Summary)

## Phase 4 — Longevity (doc 02 §3)

- SmugMug: retries on 429/5xx and the Actions cache key are done (19116ae); still to do: tolerate deleted albums, fallback when the API/seed is unreachable
- Pin `fork` start method or drop multiprocessing before any Python 3.14 bump
- Y2K39 fix in `years.py` (breaks September 2039)
- Replace `pytest-vcr`/`pydantic-collections` when they next block an upgrade

## Non-goals for now

- Speed: full build is ~15 s; the collaborators N+1 is not worth fixing
- Serving infrastructure: static S3 output is the point
