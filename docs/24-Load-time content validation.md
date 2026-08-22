---
type: task
status: todo
---

# Load-time content validation

Audit (2026-08-22, after tasks 12–21) of checks that fire at dump time or not at all but whose root cause is content, detectable at load. Convention: ERROR with content-relative path (doc 10); keep the document unless noted. Done already: `date_end` before `date_start` (d7d4dac), unrecognised season, HTML sanitisation (23).

Two homes:

- **Per-document** — pydantic validators on `models.*` or checks in `loader.load_*`, path available.
- **Post-load pass** — new `validate` step between `run_loaders()` and `dump_all()` over the populated sqlite, for cross-document checks. Does not exist yet; build it first.

`LOADERS` runs `_data/*` last; move data loaders (roles, link-types) first so show/person validators can consult them.

## Promote from dump time

| #   | Check                                                             | Today                                                                          | Do                                                                        |
| --- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| 1   | `Link.href` with disallowed scheme                                | ERROR at dump per embedding file, no path (`links.py validate_href`)           | `field_validator` on `models.Link`; drop silently at dump without logging |
| 2   | Venue id authored with divergent spellings                        | WARNING at dump, names neither shows nor spellings (`venues.py get_stub_name`) | Post-load ERROR listing show paths and spellings                          |
| 3   | Link type templates a username the link lacks → no href           | WARNING at dump (`links.py get_link_href`)                                     | Load-time ERROR after reordering loaders                                  |
| 4   | Award holder with no known/estimable graduation → on no year page | WARNING at dump (`people.py get_award_holders`)                                | Post-load ERROR                                                           |
| 5   | `homepage.py get_show_run` date-order warning                     | duplicate of loader ERROR                                                      | Remove log, keep fallback                                                 |
| 6   | Student-playwright "credited by hand"                             | load-time, uses title not path                                                 | Use `path.content_path`                                                   |

## Currently silent — add

| #   | Condition                                                                                                   | Effect today                                            | Where                        | Level               |
| --- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- | ---------------------------- | ------------------- |
| 1   | Two distinct names → same `person_id`                                                                       | people merge into one page, arbitrary name wins         | post-load                    | ERROR               |
| 2   | `playwright_alias` inert (not student_written / playwright_false / various / unknown), or alias not in crew | alias discarded                                         | `models.Show` validator      | ERROR               |
| 3   | Student-written with multi-writer name (`and`, `,`, `&`)                                                    | no crew credit, no person page                          | `models.Show` validator      | ERROR               |
| 4   | `devised`/`improvised` alongside `playwright`                                                               | playwright dropped from output and indexes              | `models.Show` validator      | ERROR               |
| 5   | Two playwright/play names → one id                                                                          | `/playwrights/index` emits duplicate ids                | post-load                    | ERROR               |
| 6   | Committee `role: unknown`/null                                                                              | credit in no role index                                 | `models.Committee` validator | WARNING             |
| 7   | Trivia naming a person with no credits and no doc                                                           | never dumped                                            | post-load                    | WARNING             |
| 8   | `Person.award` outside known set                                                                            | on person page only, not year lists                     | `models.Person` validator    | WARNING             |
| 9   | `date_start` outside the folder's academic year                                                             | wrong-year sequencing                                   | `loader.load_show`           | ERROR               |
| 10  | `graduated` before first show year or >10y after last                                                       | bad student/estimate logic                              | post-load                    | WARNING             |
| 11  | `tour` entry with neither venue nor date (sparse `jerusalem.md` case)                                       | sparse output                                           | `models.Show` validator      | WARNING             |
| 12  | `link.rating` outside 0–5; `date` unparsable                                                                | passed through                                          | `models.Link`                | ERROR               |
| 13  | `content` that is only an HTML comment placeholder                                                          | leaks to plaintext (sanitiser now strips; leaves empty) | `loader`                     | INFO                |
| 14  | `course`/`careers` scalar not list                                                                          | accepted                                                | `models.Person`              | DEBUG count         |
| 15  | `PersonRef` role with `name: null`                                                                          | `ShowRole(person=None)`                                 | `models.PersonRef`           | check volume first  |
| 16  | Image asset `type` matching no category                                                                     | show reported poster-less                               | `models.Asset`               | INFO                |
| 17  | `venue_sort` without `venue`, empty `venue`                                                                 | inert                                                   | `models.Show`                | WARNING             |
| 18  | Near-duplicate person ids (`joe_bloggs`/`joseph_bloggs`)                                                    | plan Phase 2 `nthp lint`                                | post-load                    | INFO                |
| 19  | Unknown frontmatter keys — `extra="forbid"`                                                                 | every doc 03 "silently ignored" came from this          | all models                   | ERROR; plan Phase 2 |

Keep as is: link `type` matching no definition (documented), crew role matching no definition. Delete dead branches: `history.py` image without alt (model requires both), `venues.py` `or venue_id` fallback (unreachable).

## Build vs lint

Build-time WARNING/ERROR is reserved for defects that should be fixed. Expected, advisory or long-tail conditions go to a new `nthp lint` command (plan Phase 2; does not exist yet) which runs the same post-load pass but reports rather than alarms, and never fails CI.

**Build** (defects): promote 1–4, 6; silent 1–5, 9, 12, 19; HTML sanitisation; date order.

**Lint** (expected): venue referenced without a `_venues/` file, crew role matching no definition, link type matching no definition, committee `role: unknown` (6), trivia for uncredited person (7), award outside known set (8), graduation plausibility (10), sparse tour (11), placeholder content (13), scalar course/careers (14), `PersonRef` without name (15), uncategorised image type (16), inert `venue_sort` (17), near-duplicate ids (18), `season_id IS NULL` count.

Existing build-time logs that should move to lint: `roles.py` "N crew roles match no definition" INFO, venue stub count.

## Order

1. `extra="forbid"` (19) — widest net, cheapest.
2. Per-document validators: promote 1, 3, 6; add 2, 3, 4, 8, 9, 11, 12.
3. Post-load pass scaffold, then promote 2, 4; add 1, 5, 7, 10.
4. `nthp lint` command reusing the post-load pass for the lint list above.
