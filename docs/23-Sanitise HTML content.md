---
type: task
status: done
---

# Sanitise HTML content

`content.markdown_to_html` (`nthp_build/content.py`) runs python-markdown with no sanitisation. Markdown passes raw HTML through, so `<script>`, `<iframe>`, `onerror=` attributes, `javascript:` hrefs etc. in any `_shows`/`_people`/`_venues` body land verbatim in `ShowDetail.content`, `PersonDetail.content`, `VenueDetail.content`. The site renders these as HTML, so the API is the trust boundary — content is editor-submitted via PRs and the collect form, and history shows stray HTML already (placeholder `<!-- Content for a bio here -->` comments reach `plaintext`, doc 17).

## Do

- Sanitise HTML at output, after markdown rendering, with [nh3](https://pypi.org/project/nh3/) (Rust `ammonia` bindings; maintained, the recommended bleach replacement — bleach is unmaintained since 2026-06). `nh3.clean(html, tags=…, attributes=…, url_schemes={"http","https","mailto"}, link_rel="noopener noreferrer")`.
- Allow-list, not block-list: markdown's own output (`p, a, em, strong, ul, ol, li, blockquote, code, pre, h1–h6, br, hr, img, table/thead/tbody/tr/th/td`) plus whatever legitimate raw HTML the content uses — audit with `rg -n '<[a-z]' content/_shows content/_people content/_venues` and list what must survive before choosing the set. Strip HTML comments.
- `plaintext` (search corpus): strip comments and tags there too; `markdown_to_plaintext` currently leaks comments.
- Log at ERROR with the document path when sanitisation changes the output, listing the tags and attributes removed, so editors see what was taken out; consider a `nthp lint` check.
- Tests: script tag, event attribute, `javascript:` href, iframe, comment, and a round-trip of ordinary markdown unchanged.
- Add `nh3` to `pyproject.toml`; it ships wheels for all CI platforms.

## Notes

- Sanitising at the API rather than the site matches ADR-17 (no site-side defensive work) and protects any future consumer.
- `Link.href` / `hrefSnapshot` are URLs, not HTML — validate scheme (`http`/`https`) there too; a `javascript:` href in a link list is the same class of problem.

## Outcome

Audit of `_shows`/`_people`/`_venues` found no legitimate raw HTML: four `<!-- … -->` placeholder comments and one escaped `\</search?q=…\>` in a show body. The allow-list is therefore markdown's own output only (`nthp_build/content.py`), with `script`/`style` content dropped and URL schemes limited to `http`, `https`, `mailto`. Two documents are altered by sanitisation today, both placeholder comments in bios.
