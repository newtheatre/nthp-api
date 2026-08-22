---
type: task
status: done
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

| #   | Condition                                                                                                   | Effect today                                                                                                                                                        | Where                        | Level               |
| --- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | ------------------- |
| 1   | Two distinct names → same `person_id` **without** a `_people/` doc                                          | can be valid (credit under a variant name); a person doc usually exists and fixes the canonical name. Flag only when no doc exists, so the dumped name is arbitrary | post-load                    | lint                |
| 2   | `playwright_alias` inert (not student_written / playwright_false / various / unknown), or alias not in crew | alias discarded                                                                                                                                                     | `models.Show` validator      | ERROR               |
| 3   | Student-written with multi-writer name (`and`, `,`, `&`)                                                    | no crew credit, no person page                                                                                                                                      | `models.Show` validator      | ERROR               |
| 4   | `devised`/`improvised` alongside `playwright`                                                               | playwright dropped from output and indexes                                                                                                                          | `models.Show` validator      | ERROR               |
| 5   | Two playwright/play names → one id                                                                          | `/playwrights/index` emits duplicate ids                                                                                                                            | post-load                    | ERROR               |
| 6   | Committee `role: unknown`/null                                                                              | credit in no role index                                                                                                                                             | `models.Committee` validator | WARNING             |
| 7   | Trivia naming a person with no credits and no doc                                                           | never dumped                                                                                                                                                        | post-load                    | WARNING             |
| 8   | `Person.award` outside known set                                                                            | on person page only, not year lists                                                                                                                                 | `models.Person` validator    | WARNING             |
| 9   | `date_start` outside the folder's academic year                                                             | wrong-year sequencing                                                                                                                                               | `loader.load_show`           | ERROR               |
| 10  | `graduated` before first show year or >10y after last                                                       | bad student/estimate logic                                                                                                                                          | post-load                    | WARNING             |
| 11  | `tour` entry with neither venue nor date (sparse `jerusalem.md` case)                                       | sparse output                                                                                                                                                       | `models.Show` validator      | WARNING             |
| 12  | `link.rating` outside 0–5; `date` unparsable                                                                | passed through                                                                                                                                                      | `models.Link`                | ERROR               |
| 13  | `content` that is only an HTML comment placeholder                                                          | leaks to plaintext (sanitiser now strips; leaves empty)                                                                                                             | `loader`                     | INFO                |
| 14  | `course`/`careers` scalar not list                                                                          | accepted                                                                                                                                                            | `models.Person`              | DEBUG count         |
| 15  | `PersonRef` role with `name: null`                                                                          | `ShowRole(person=None)`                                                                                                                                             | `models.PersonRef`           | check volume first  |
| 16  | Image asset `type` matching no category                                                                     | show reported poster-less                                                                                                                                           | `models.Asset`               | INFO                |
| 17  | `venue_sort` without `venue`, empty `venue`                                                                 | inert                                                                                                                                                               | `models.Show`                | WARNING             |
| 18  | Near-duplicate person ids (`joe_bloggs`/`joseph_bloggs`)                                                    | plan Phase 2 `nthp lint`                                                                                                                                            | post-load                    | INFO                |
| 19  | Unknown frontmatter keys — `extra="forbid"`                                                                 | every doc 03 "silently ignored" came from this                                                                                                                      | all models                   | ERROR; plan Phase 2 |

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

## Results

Done in four commits against content at 2026-08-23. Counts are from
`SMUGMUG_FETCH=false ./nthp build content` and `./nthp lint content`.

### 1. `extra="forbid"`

Keys the content uses systematically were modelled rather than left to error:
`gender` (686 people), link `author` (351 links), `contact_allowed` (95),
`published` (68 shows), committee `title` (44), venue `title_short` (8), show
`note` (7), person `alias` (3) and `aliases` (3), asset `comment`, and the
presentation keys of `_data/roles.yaml` (`icon`, `show`) and
`_data/link-types.yaml` (`icon`, `data`), which the models had documented as
ignored. `career` and tour `notes` were aliased by validators that expanded the
dict before popping the authored key, so the alias never took the key away;
both are fixed.

What is left is junk, and each one costs its document — 15 more documents fail
validation than before, all fixable in the content repo:

| Key                    | Documents                                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `adapted`              | `_shows/09_10/hamlet.md`, `_shows/13_14/a_servant_to_two_masters.md`, `_shows/75_76/the_picture_of_dorian_gray.md` |
| `adapter`              | `_shows/19_20/still_alice.md`, `_shows/23_24/doctor_faustus.md`                                                    |
| `awards`               | `_people/elle_ororke.md`, `_people/nicola_fox.md`                                                                  |
| `canonical[].name`     | `_shows/07_08/bouncers_shakers.md`                                                                                 |
| `Music, Book & Lyrics` | `_shows/09_10/the_last_5_years.md`                                                                                 |
| `categories`           | `_shows/11_12/be_my_baby.md`                                                                                       |
| `start_date`           | `_shows/75_76/smoking_is_bad_for_you.md`                                                                           |
| `traslator`            | `_shows/75_76/the_possessed.md`                                                                                    |
| `playright`            | `_shows/97_98/the_trial_spring.md`                                                                                 |
| `website`              | `_venues/sweet-venues.md`                                                                                          |
| `Careers`              | `_people/emma_pallett.md`                                                                                          |

(`_people/nick_gill.md` already failed, on an unparsable `submitted` date.)

### 2. Per-document checks

Findings 2, 3, 4 and 9 report from `loader.check_show` rather than a pydantic
validator: a raised `ValueError` costs the document, and the convention is to
keep it. Findings 1 and 12 do raise, in `models.Link`, as nothing in the content
trips them.

| Check                                    | Findings |
| ---------------------------------------- | -------- |
| student writer names several people      | 31       |
| `date_start` outside the folder's year   | 5        |
| `date_end` before `date_start`           | 2        |
| student credit written by hand (WARNING) | 2        |
| inert `playwright_alias`                 | 0        |
| `devised`/`improvised` with a playwright | 0        |
| link type templating an absent username  | 0        |
| disallowed URL scheme                    | 0        |
| rating outside its scale                 | 0        |

Ratings are authored as `4/5` or `8/10`, not as a bare 0–5, so the validator
takes a score out of a total and checks the score against it.

### 3. Post-load pass

`nthp_build/validate.py`, run by `nthp load` and `nthp build` between
`run_loaders()` and `dump_all()`. 7 defects:

| Check            | Findings |
| ---------------- | -------- |
| play ids         | 6        |
| playwright ids   | 1        |
| venue spellings  | 0        |
| award graduation | 0        |

### 4. `nthp lint`

`nthp lint <path>` loads into an in-memory database and reports the lint list
through `rich`, in `cli/lint_report.py`: a heading per check with its count, a
line on what the check means and how to fix it, a table of file, value and cost,
and a closing summary table coloured by severity (amber worth fixing, cyan
advisory). `--check NAME` runs one, `--verbose` lists every finding rather than
the first dozen, and `--format plain` drops colour and boxes, as does any
non-terminal. A check whose findings repeat the same value — `course` fifty
times over — collapses to value and count instead of one row per document. Build
logging is untouched: plain logging, as before.

638 findings, none of them failures:

| Check                     | Findings |
| ------------------------- | -------- |
| crew role definitions     | 424      |
| near-duplicate person ids | 66       |
| scalar `course`/`careers` | 50       |
| venues without a document | 37       |
| link type definitions     | 17       |
| tour dates                | 12       |
| person name collisions    | 9        |
| image categories          | 9        |
| committee roles           | 5        |
| graduation plausibility   | 5        |
| placeholder content       | 2        |
| trivia people             | 1        |
| credits without a name    | 1        |
| awards outside the set    | 0        |
| inert `venue_sort`        | 0        |
| shows without a season    | 0        |

Two of the lint list cannot be seen from sqlite — a body that is only an HTML
comment, and `course`/`careers` authored as a bare value — as both are gone by
the time the document is stored. The loader records those in a `LoadFinding`
table for lint to report.

Near-duplicate ids use a heuristic: same surname, forenames sharing their first
two characters and alike enough over the whole name, which catches `joe`/`joseph`
without dragging in every `c*_jones`.

### 5. Removals

`homepage.get_show_run`'s date-order warning, the dump-time venue spelling and
award graduation warnings, `roles.log_crew_roles_without_definition`, and the two
dead branches (`history.py` image without alt, `venues.py` `or venue_id`).

### Not done

Finding 15's volume was checked rather than assumed: one credit in the whole
archive has a role and no name, so it stays in lint.
