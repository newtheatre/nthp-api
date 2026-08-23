---
type: task
status: done
---

# SmugMug inventory for editors

Replaces the old site's `/util/smug-*` pages. Those had the browser call SmugMug directly (public API key in `utility.coffee`, `count=5000`) for a whole album, then joined against Jekyll-built `/feeds/smug_*.json` usage maps. They got slower as the albums grew and leaked the key. The new site 410s `/util/*` (web doc 20) and will render `/editors/smugmug*` from JSON the API builds here.

Editors need three answers:

1. **Find a key** — which ImageKey/AlbumKey is this file? (search by filename/title, see thumb, copy key)
2. **Unused** — in SmugMug, referenced by no show/person/venue
3. **Broken** — referenced in content, but SmugMug cannot describe it

Usage is a content fact, so the join lives in the API (web ADR-17), not the site.

## Output

New static JSON under `/editors/`, same build as everything else, in the OpenAPI spec:

```
/editors/smugmug/albums.json        SmugMugAlbumInventory[]
/editors/smugmug/album/{key}.json   SmugMugImageInventory
/editors/smugmug/broken.json        SmugMugBrokenRef[]
```

```ts
type AssetUse = {
  targetType: 'show' | 'person' | 'venue';
  targetId: string;        // show id `YYYY-YY/slug`, person id, venue id
  title: string;           // show title / person name / venue name
  role: string;            // 'poster' | 'headshot' | 'album' | 'asset' | 'photo' … the asset category
};

type SmugMugAlbumInventory = {
  key: string;
  name: string;
  urlName: string;
  webUri: string;
  imageCount: number;
  lastUpdated: string | null;
  usedBy: AssetUse[];      // shows whose `album` asset is this key
};

type SmugMugImageInventory = {
  album: Omit<SmugMugAlbumInventory, 'usedBy'>;
  images: {
    key: string;
    fileName: string;
    title: string | null;
    width: number | null;
    height: number | null;
    isVideo: boolean;
    uploadedAt: string | null;
    webUri: string;
    usedBy: AssetUse[];    // empty = unused
  }[];
};

type SmugMugBrokenRef = AssetUse & { key: string; reason: string };
```

Image `usedBy` is computed over every bare-key reference in content (posters, headshots, venue photos, show assets, trivia `targetImageId`), not only the album the image sits in — an image used from an album other than its own still counts as used.

## Do

- `smugmug.py` only fetches albums that a show references. Add a sweep of `user/newtheatre!albums` (paginate via `get_pages`, not `count=5000`) so the album table is complete, and fetch images for the configured utility albums — headshots `hZh8Jt`, show assets `C87GJX` and `j3PdMh`, venues `BdFr84` — in content config (22), not hardcoded. Cache both in `nthp.smug.db` like the rest (06, 20); honour `SMUGMUG_FETCH=false` by emitting from cache only.
- Build a key → uses map from `database.Asset` (`target_type`, `target_id`, `asset_category`) plus trivia image refs; join in the dumper. One pass, not per image.
- `broken.json` is the list `update_images` already logs as `No dimensions for image …` — emit it instead of logging it away. Include the reason (404 vs no dimensions vs fetch failed) so a transient 429 isn't reported as a dead key.
- `albums.json` and `broken.json` are small. A utility album may reach low thousands of images; one file per album is fine (~200 B/image). Do not paginate unless a file passes ~1 MB.
- Spec coverage test (`test_dump_spec_coverage`) for the three paths; fixture-based tests for the join: used, unused, used-from-other-album, broken.
- `/editors/*` stays out of any sitemap/search corpus the API builds.

## Don't

- No live SmugMug calls at request time; no key anywhere outside the build.
- Don't fetch images for every album in the account — only the utility albums and referenced show albums. Unreferenced production-shot albums appear in `albums.json` as unused, which is the point.

## Questions

Q: Is `j3PdMh` still a live show-assets album or historical? Old `utility.coffee` treated both as show assets.
A: Yes
Q: Rotate the SmugMug API key committed to `history-project/_coffee/scripts/utility.coffee` — not this repo's job but this is where it's noticed.
A: Read-only no need
Q: Utility album keys in content config (22), which is not built yet?
A: API settings for now — `config.smugmug_utility_album_keys`, env-overridable. Moves to content config when 22 lands.

## Done

Three files, as specced, written by `dumper.dump_editors` from `editors.py`:

- `smugmug.get_user_albums` sweeps `user/{nickname}!albums` via `get_pages`,
  cached in `nthp.smug.db` under a `user-albums:` namespace like everything else.
  The nickname is `SMUGMUG_NICKNAME`, default `newtheatre`. The sweep writes a
  `database.SmugMugAlbum` row per album, so the dumper reads one database;
  images are fetched only for the utility albums and the albums a show
  references, and their rows carry the image collection.
- The sweep does not list the utility albums — 485 albums, none of them, which
  is why the old page reached them by key alone. So any album in the fetch list
  the sweep misses is asked about with `album/{key}` (`smugmug.get_album`,
  cached under an `album:` namespace) rather than dropped.
- `editors.get_uses_by_key` is the one pass: every SmugMug asset row plus the
  trivia image refs, keyed by SmugMug key, titles looked up once per record
  type. A trivia ref to a key its own record already uses is not repeated.
- Reasons survive the cache: `SmugMugImageInfo` gained `error`
  (`not_found` / `no_dimensions` / `fetch_failed`), so `update_images` records
  the failure on the asset rather than logging it away. An entry cached before
  reasons existed — no dimensions, no reason — is asked about again rather than
  read as a silent failure, so `broken.json` fills in on the next build with a
  key. A key the build never asked about (no API key, cache-only) is unknown,
  not broken, and is left out.
- `test_editors.py` covers used, unused, used-from-another-album, broken with
  each reason, and that the dump adds nothing to the search corpus;
  `test_dump_spec_coverage` covers the three paths.

Utility album keys live in `config.smugmug_utility_album_keys` (defaults
`hZh8Jt`, `C87GJX`, `j3PdMh`, `BdFr84`), not content config — task 22 has no
infrastructure yet, so they move there with the rest.

Needs a build with `SMUGMUG_API_KEY` to fill: from the cache alone the sweep
and the by-key album fetches return nothing.
