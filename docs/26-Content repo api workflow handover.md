---
type: task
status: todo
---

# Content repo `api.yml` handover

`history-project/.github/workflows/api.yml` installs `nthp_api` from PyPI and runs `nthp build .` on every push/PR, deploying to S3. It has not been touched during tasks 12–25. What needs to change, and what does not.

## Must change

1. **Release nthp-api** — the workflow does `pip install -U nthp_api`, so nothing lands until a PyPI release. Everything since 0.3.0 is breaking (year ids, shapes, removed `/trivia/*`); bump to **0.4.0**. Confirm the release workflow/`uv build` still works and `nthp version` prints it.
2. **SmugMug cache key** — `key: smugmug-1` is a fixed key: the cache is restored but never re-saved, so the 1454-image `sizedetails` sweep (task 20) would re-run on every build. Copy the fix from `nthp-api/.github/workflows/build.yml`:
   ```yaml
   key: smugmug-${{ github.run_id }}
   restore-keys: |
     smugmug-
   ```
   Also `actions/cache@v6` is fine; keep.
3. **First run after release** makes ~1500 SmugMug image calls (concurrency 10, retries on 429/5xx). Accept once; subsequent runs hit the cache. Alternatively warm the seed: run locally with the key, then upload `nthp.smug.db` to `nthp-seed` S3 so `wget -nc` fetches a pre-enriched db.
4. **Python 3.14** — the workflow uses `python-version: '3.14'`; nthp-api is developed on 3.13. Plan Phase 4: pin the `fork` multiprocessing start method (or drop multiprocessing) before trusting 3.14 — the dumper's parallel step depends on it. Also confirm `nh3` (task 23) and all deps have 3.14 wheels. Safest: set `'3.13'` until verified.

## Should change

5. **Add `nthp lint .`** as a step after build (task 24): reports expected content issues, never fails. Print to the job log; optionally post as a PR comment later.
6. **Surface build errors** — `nthp build` now logs ERROR for real defects (bad dates, unknown frontmatter keys with `extra="forbid"`, sanitised HTML, bad link schemes). Decide whether ERRORs fail the job (plan Phase 1: nonzero exit with a shrinking allowlist). Until that lands, errors only show in the log.
7. **Site stats build metadata** — `SiteStats.commit`/`buildNumber`/`branch` read `GITHUB_SHA`, `GITHUB_RUN_NUMBER`, `GITHUB_REF_NAME` (task 25). GitHub sets these automatically; no workflow change. `BRANCH` env still wins if set — `_bin/deploy_vars.sh` may set it; check it matches `ref_name`.

## No change needed

- `SMUGMUG_API_KEY` secret — same name, same usage. Missing key now degrades to one warning and omitted dimensions rather than a crash.
- S3 deploy, `_bin/deploy.sh`, `_bin/deploy_vars.sh`, GitHub deployments, PR previews — untouched; output is still `dist/`.
- `.s3deploy.yml` headers — `max-age=180` not load-bearing for the new site (doc 11 §Caching); S3 ETag/Last-Modified suffice.
- Content-repo directory rename (`_shows/24_25` → `2024-25`) — deferred until the new site launches; loader still reads `YY_YY`.

## Later (task 22)

Once committee-role aliases, season definitions and venue sentinels move to `_data/*.yaml` / `_venues/*.md` in the content repo, those files must exist before the corresponding nthp-api release is picked up — sequence the two PRs.
