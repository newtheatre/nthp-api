---
type: task
status: open
---

# API docs site

Publish a human-readable docs site alongside the API: a single HTML page
rendering `openapi.json` with [Stoplight Elements](https://github.com/stoplightio/elements),
served as `index.html` at the root of the deployed API.
[spec.html](spec.html) in this folder is the working example.

## The page

A static file checked into the repo — no templating needed. Suggested home:
`nthp_api/nthp_build/static/index.html` (new directory, alongside the code
that copies it).

Changes from the example:

- **Relative spec URL**: `apiDescriptionUrl="openapi.json"`, not the absolute
  `https://content.nthp.wjdp.uk/v1/master/openapi.json`. The example's
  hardcoded path is already wrong (deploy.sh ships to `v1/nthp-api-master`,
  not `v1/master`) — proof enough that the page should locate the spec
  relative to itself. Elements resolves relative URLs against the page.
- **Pin the Elements version**: the example loads
  `unpkg.com/@stoplight/elements/…` unpinned — floats to latest, which is
  exactly the CI/CDN rot the project review warns about. Pin to the current
  major (e.g. `@stoplight/elements@9`), or a full version.
- Keep `router="hash"` (no server-side routing on S3) and `layout="sidebar"`.

## Build wiring

- `dumper.py`: `dump_all()` copies the static file to
  `OUTPUT_DIR / "index.html"` (`OUTPUT_DIR` is `dist`, `dumper.py:38`) —
  plain copy in the parent, no new dumper process. `openapi.json` is already
  written at the same level (`dumper.py:60`), so the relative URL works
  locally too: `python -m http.server` in `dist/` shows the docs.
- `.s3deploy.yml`: only `.json` files get a `Cache-Control` route today. Add
  an equivalent route for `.html` (`max-age=180, public`) so a redeployed page
  doesn't stick in caches.

## Tests / verification

- Dump test: after a dump, `dist/index.html` exists and references
  `openapi.json` relatively (guards against someone reintroducing an absolute
  URL).
- Manual: serve `dist/` locally, confirm the page renders the spec.

## Decisions

1. Pin Elements via unpkg rather than vendoring the JS/CSS into the repo.
   Vendoring would make the page immune to unpkg outages/disappearance, but
   costs a few MB in-repo and a manual update path; if unpkg dies the API
   itself is unaffected — only the docs page goes blank. Revisit if that
   trade-off feels wrong.
2. Delete `docs/spec.html` once implemented — the real page in
   `nthp_api/nthp_build/static/` becomes the reference.
3. No chrome — bare Elements with a sensible `<title>` is fine.
