---
type: review
status: open
---

# nthp-api Strictness Review

*Assessed 2026-08-18. Companion to [02-Project review](02-Project%20review.md) and
[03-Completeness review](03-Completeness%20review.md).*

Context: validation is currently lax because this is not yet the production
build. The goal is to get stricter and fix up issues hidden in the source repo.
Grounded in a survey of the live content repo (1,049 shows, ~750 people).

## What today's 6 failures actually are

Of the documents currently failing validation, **5 are the schema being wrong
for an archive, 1 is bad data**:

| Document | Value | Verdict |
|---|---|---|
| `_shows/00_01/waiting_for_dildo.md` `date_start` | `2001-06` | Legitimate partial date |
| `_people/katie_rowley-jones.md` `news.0.date` | `2002-05` | Legitimate partial date |
| `_shows/04_05/shoe_story.md` `links.0.date` | `2005` | Year-only; YAML parses as int, pydantic reads int as unix timestamp → confusing "zero time" error |
| `_shows/06_07/twinss.md` `links.0.date` | `2007` | Same |
| `_shows/78_79/the_wit_to_woo.md` `links.0.date` | `2000` | Same |
| `_people/nick_gill.md` `submitted` | `04/01/2017` | Genuinely malformed — **fix in source** (`2017-01-04`) |

## Too strict: dates

An archive is built on incomplete information; the schema should model date
precision instead of rejecting it.

**Introduce a fuzzy date type** for `Show.date_start` / `date_end`,
`Link.date`, `Trivia.submitted`, `Person.submitted`:

- **Accept**: `datetime.date` (YAML's parse of a full date), `str` matching
  `YYYY` or `YYYY-MM`, and `int` (YAML's parse of a bare year). Normalise to a
  precision-aware value.
- **Output**: ISO 8601 reduced-precision strings — `"2001"`, `"2001-06"`,
  `"2001-06-14"`. Lexicographically sortable; consumers read precision from
  length. Where SQL sorting matters (`Show.date_start` column), store the
  first day of the known period alongside.
- Clears 5 of the 6 current failures with the data as-is.

**Keep as-is** (appropriately lax for an archive):

- `Person.submitted: date | bool` — `true` = "submitted, date unknown".
- `unknown` sentinel values for role/name — they are spec'd.
- `PermissiveStr` on note-ish fields.

## Not strict enough — ranked

1. **Exit code.** Everything below is worthless while failures exit 0 and
   deploys proceed with content silently missing. Nonzero exit on any
   validation error, plus an **allowlist file for grandfathered documents** so
   the existing backlog doesn't block deploys while new breakage fails
   immediately. (Also doc 02 §1.3.)

2. **`extra="forbid"` on ingest models.** The models default to
   `extra="ignore"`, so a typo'd or unmodelled frontmatter field vanishes
   without a word — this is how `tour`, `careers`, `playwright_alias` are
   dropped today (see doc 03). Forbid extras and explicitly
   model-or-reject every spec field.

3. **`season` / `period` enums.** Live data has 17 season values against the
   spec's 10 — the spec is stale, the extra values are real (`UNCUT`,
   `Studio`, `Postgrads`, `Creatives`, `Previews`, `BedFest`). Periods contain
   typos an enum would have caught: `spring` (lowercase, 1 doc), `unknown`
   (1 doc). Curate the real list in code (or read from the content repo's
   `_data`), reject anything else.

4. **Cross-reference checks as lint, not errors.** 36 of 67 venue ids
   referenced by shows have no venue document — `unknown` ×27, `youtube` ×20,
   then a tail of Edinburgh venues (`c-soco`, `zoo-monkeyhouse`, …). Some are
   deliberate placeholders, so a hard error is wrong, but a lint report keeps
   the list visible so genuine typos don't hide among them.

5. **Date sanity checks.** `date_end >= date_start`; `date_start` within the
   academic year of the show's folder (Sept–Aug window — cheap, catches
   misfiled shows); `graduated` within a plausible range.

6. **Spec conformance currently ignored.** `season_sort` is `required: true`
   in the spec but `Optional` in the model; person/venue `title` must match
   the filename per spec — neither is checked.

7. **Person identity lint — but not the naive version.** `person_id` is the
   slugified free-text name, so one misspelling silently splits a person's
   history across two records. 1,751 of 3,466 people have exactly one credit,
   so flagging singletons would drown in noise. Instead lint **near-duplicate
   ids**: edit distance 1, or same name modulo diacritics/hyphenation/case.

8. **Role names — only after fixing the definitions.** 500 of 519 distinct
   crew role strings match nothing in `roles.py`, including the most common
   roles in the archive (Technical Operator ×686, Stage Manager ×583, Set
   Designer ×214). Adopt the content repo's `roles.yaml` (31 roles + aliases)
   first; then an unmatched-role lint becomes signal instead of noise.

## Mechanism: two tiers, honestly separated

- **Errors — fail the build**: schema violations, forbidden extra fields, enum
  violations, malformed dates. Minus the grandfathered allowlist, which should
  only ever shrink.
- **Lint — `nthp lint`, reported and counted, never fails**: phantom venues,
  near-duplicate people, unmatched roles, incomplete-cast heuristics. Run in
  CI so the report stays current; burn it down in the source repo over time.

## Immediate source-repo fixups

| File | Fix |
|---|---|
| `_people/nick_gill.md` | `submitted: 04/01/2017` → `2017-01-04` |
| (1 show) | `period: spring` → `Spring` |
| (1 show) | `period: unknown` → omit |

The remaining 4 current failures become valid data once fuzzy dates land —
fix the schema, not the data.
