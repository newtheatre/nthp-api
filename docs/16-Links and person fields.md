---
type: task
status: todo
---

# Links and person fields

Web doc 30 §6; 03 summary items 1–4. Largest gap: `Link` is ingested everywhere and output nowhere; person `course`/`careers` silently ignored; `award`/`links`/`news` ingested and dropped; `playwright_alias`/`playwright_false` produce wrong crew lists.

## Output

`Link` schema (new, public): `type, href, username, title, date, publisher, rating, quote, note` + resolved `href` for templated types (`https://twitter.com/{username}`) + link-type metadata from `_data/link-types.yaml` (name, icon-free).

- `ShowDetail.links: Link[]` (press reviews)
- `VenueDetail.links: Link[]`
- `PersonDetail` gains `course?: string[]` (coerce string→list), `award?: "Fellowship" | "Commendation"`, `careers?: string[]` (accept `careers:` and `career:`), `links?: Link[]`, `news?: Link[]`, `student: boolean`
- `YearDetail.fellows[]`, `commendations[]` (Ruby site generates both; needs `award`)
- "Then/Now" is a metadata split, not a bio split — do **not** split `content`.

## Do

- `student` from `config.graduation_month`/`graduation_recency_limit` alongside `get_graduation`; note in spec that it depends on build date.
- `playwright_alias`: attribute the playwright crew credit to the aliased person id; `playwright_false`: keep/remove playwright from crew per flag. Add tests with real content cases.
- Load `_data/link-types.yaml` and `_data/careers.yaml` from content.
- `hrefSnapshot` (archive.is URL) generated on every `Link`, as the Ruby site did.
- Key events (`history/index.json`) gain `image?: {href, alt}` (03: silently ignored).
