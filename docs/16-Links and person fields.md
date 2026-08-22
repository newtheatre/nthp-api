---
type: task
status: done
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

## Notes

- `award` values in content are wider than the two the year pages use: `Fellowship`, `Commendation`, `Merit`, `Union Prize`. The enum takes all four; `YearDetail.fellows`/`commendations` take the first two.
- `careers.yaml` is not loaded: the Ruby site only uses it for the collection form's checkboxes, never to canonicalise a record, so careers are output as authored.
- Link types are matched case-insensitively and output under the name `link-types.yaml` gives; types with no definition keep the authored name. The `default` type carries nothing but an icon, so it is no fallback.
- `playwright_false` appears nowhere in the content; its behaviour is covered by tests only.
- Nick Gill holds a Fellowship but his record fails validation on an invalid `submitted` date, so he is missing from 2015-16's fellows. A content fix, see [10](10-Invalid%20YAML.md).
