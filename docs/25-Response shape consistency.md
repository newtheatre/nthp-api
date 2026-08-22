---
type: task
status: done
---

# Response shape consistency

Review 2026-08-22 of `schema.py` after tasks 12–21, against web doc 30. No consumers yet, so breaking changes are free — do this before the site build starts. Ranked by consumer impact.

## Findings

| #   | model.field                           | Current                                                                                                                                                                          | Proposed                                                                                   |
| --- | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| 1   | `YearList`/`YearDetail`               | `yearId` + `title` both `2013-14`, no `id`                                                                                                                                       | `id`; keep `title`; drop `yearId` (doc 30 §10)                                             |
| 2   | `ShowDetail`/`ShowList`               | no `yearId`/`year`; consumer splits `id`                                                                                                                                         | add both (additive)                                                                        |
| 3   | `/roles/crew/index.json`              | `Role` has no `id`; committee index has `RoleWithId`                                                                                                                             | one `Role` with `id` everywhere (doc 30 §11: never derive URLs from names)                 |
| 4   | required-but-nullable                 | `HistoryRecord.yearId`, `BaseTrivia.submitted`, `TargetedTrivia.personId/personName`, `PersonTrivia.targetImageId/targetYear` have no default → spec says required, dumper omits | `= None` on every nullable; spec `required` must match output                              |
| 5   | person display name                   | `PersonList.name` vs `.title` on five other person models; `personName`, `showTitle` flattened                                                                                   | rule 3 below                                                                               |
| 6   | committee vs cast/crew ref            | `YearDetail.committee` is raw `PersonRoleList {personId, personName, role, isPerson, note, comment}`; cast/crew is `{role, person: PersonList, note}`; leaks editorial `comment` | same shape as cast/crew                                                                    |
| 7   | images — four shapes                  | `PersonDetail.headshot: Asset`; other `headshot: str`; `imageId`/`targetImageId`/`primaryImage` bare keys; `HistoryRecordImage {href, alt}`                                      | rule 4: `Asset` in detail, `{id, width, height}` in lists, named by role                   |
| 8   | `PersonShowRoleItem.roleType`         | `"CAST"`/`"CREW"` str                                                                                                                                                            | lowercase enum                                                                             |
| 9   | `ShowMissingField` values             | snake_case `date_start`                                                                                                                                                          | camelCase matching field names                                                             |
| 10  | `SearchDocumentPerson.graduationYear` | `str` `"2015-16"` (a year id); doc 30 says number                                                                                                                                | `graduationYearId: str` + `graduationYear: int`                                            |
| 11  | `PersonGraduated.yearTitle`           | `"2016"` while other `yearTitle` are `"2013-14"`                                                                                                                                 | `{yearId, yearTitle, gradYear, decade, estimated}`                                         |
| 12  | counts                                | `Role.count` vs `showCount`, `showRoleCount`…                                                                                                                                    | `{singularNoun}Count`, no bare `count`                                                     |
| 13  | empty list vs omission                | per construction site: people emit `careers: []`, shows omit `company`                                                                                                           | enforce in `write_file`: lists always present, null scalars omitted                        |
| 14  | `ShowList` ⊄ `ShowDetail`             | `ShowList.devised: str\|bool`, `season: str\|None`; detail lacks `devised`, `season` required; `ShowIndexItem` has `playwrightDescriptor` not `playwright`                       | strict subsets; `devised: bool`                                                            |
| 15  | `PersonDetail.submitted`              | `FuzzyDate\|bool\|None`                                                                                                                                                          | `submittedDate: FuzzyDate\|None` (+ `submitted: bool` if meaningful)                       |
| 16  | nested refs                           | `{id,title}` / `{id,name}` / flattened `showId, showTitle, showYearId…`                                                                                                          | one `ShowRef`/`VenueRef`/`PersonRef`/`YearRef` each, reused; flatten only in search docs   |
| 17  | `SearchDocumentShow.playwright`       | descriptor string named `playwright`                                                                                                                                             | `playwrightDescriptor` as in `ShowIndexItem`                                               |
| 18  | trivia                                | `TargetedTrivia` vs `PersonTrivia` asymmetric                                                                                                                                    | one `Trivia {quote, submitted, person?: PersonRef, target?: {id,type,title,image,yearId}}` |
| 19  | `Asset.date`                          | `str` timestamp                                                                                                                                                                  | `datetime`, `uploadedAt`                                                                   |
| 20  | `decade`                              | `int` `201`                                                                                                                                                                      | `2010` (start year); unify `yearDecade`/`decade`                                           |
| 21  | spec params                           | `/roles/*/{name}`                                                                                                                                                                | `{id}`                                                                                     |
| 22  | `PersonList.name`                     | optional                                                                                                                                                                         | required                                                                                   |
| 23  | `VenueList.venueSort`                 | named after sort key                                                                                                                                                             | `group`                                                                                    |
| 24  | `SiteStats`                           | `showsWithImageCount` plural                                                                                                                                                     | singular noun prefix                                                                       |

Confirmed fine: every path has a model, bare arrays throughout, `SearchDocument` discriminator, dist matches spec paths.

## Rules

1. Own id is `id`; never `{type}Id` on a record's own id.
2. References: `{entity}Id: string` flat, or a nested ref object — never both names for one concept. One ref shape per entity type, defined once.
3. Display string: `title` for shows/people/plays/years; `name` for venues/seasons/playwrights. Never both.
4. Images: `Asset` in detail; `{id, width, height}` in lists, named by role (`headshot`, `primaryImage`). Never a bare string.
5. Counts: `{singularNoun}Count`.
6. Enums: lowercase values; value spells the camelCase field it refers to.
7. Dates: `FuzzyDate` strings for content dates; `datetime` named `*At`/`*Time` for machine timestamps. No `str|bool` unions.
8. Nullable ⇒ default in model so spec `required` is honest. Lists always emitted; null scalars omitted.
9. `XIndexItem ⊂ XList ⊂ XDetail`, identical names/types/optionality.

## Do

Apply in one pass (every item is breaking anyway), update web doc 30's TS types to match, tests and spec. Encode rules 8 and 9 as tests over the schema module so they hold.

## Done (2026-08-22)

All 24 findings applied and all 9 rules enforced, in one pass. Shared refs live in `schema.py` and are reused everywhere: `ImageRef`, `PersonRef`, `VenueRef`, `YearRef`, `ShowRef` (plus `ShowDatedRef` for date-ordered lists), `PlayRef`, `PlaywrightRef`. `Asset` extends `ImageRef`, so a detail image is a list image with more on it. Rules 8 and 9 are tests over `schema.py` (`tests/test_nthp_build/test_schema.py`).

Rule 8 is enforced structurally rather than per call site: no schema field is both a list and nullable, every nullable field has a default, and `dumper.write_file` serialises with `exclude_none=True` and nothing else. `exclude_unset` is gone; nothing relied on it, so fields left at their defaults (`tour`, `links`, `assets`, `aliases`, …) now always appear.

Handled differently from the table above:

- **11, rule 1** — `PersonGraduated` is a `YearRef` with `estimated` on it, so its fields are `id`, `title`, `startYear`, `gradYear`, `decade`, not `yearId`/`yearTitle`. Reusing the ref keeps rule 1 (own id is `id`) and rule 2 (one ref shape per entity). `PersonCommitteeRole` and `PersonCommitteeRoleList` nest `year: YearRef` for the same reason.
- **18** — the trivia date is `submittedDate`, matching `PersonDetail.submittedDate`; `submitted` means a boolean everywhere. The target is a `ShowRef` plus `type`, so its image is `primaryImage`, named by role as rule 4 wants, rather than `image`.
- **3, 12** — `Role` gained `id` and `count` became `holdingCount`; `role` also became `name`, as a role is a named thing like a season and `Role.role` read as a reference to itself.
- **6, 16** — cast, crew and committee share one `PersonCredit {role, person: PersonRef, note}`; the editorial `comment` is gone from output. `PersonList` became `PersonRef` and its `name` became `title` (rule 3), required (22).
- **9** — `PosterItem` is a `ShowRef` whose `primaryImage` is required, rather than flattened `showId`/`showTitle`/`imageId`; `OnThisDayShow` and the show sequence items are `ShowRef`s too.
- **rule 9** — `PersonDetail` gained `hasBio`, `showRoleCount` and `committeeRoleCount` so `PersonIndexItem ⊂ PersonDetail` holds. The subset test allows the detail model to carry a subclass of the list model's type, which is what rule 4 asks for on `headshot`.
- **Search documents** keep flat `{entity}Id` fields and a bare `imageId`, documented on `SearchDocumentBase`. Their optional lists became always-emitted empty lists: rule 8 beats the few bytes.
- **`HistoryRecordImage {href, alt}`** stays as it is. Those are external URLs with captions, not asset-store images, so rule 4 does not apply.
- **`decade`** is the start year of the decade (`2010`), in `YearRef`, both search documents and `PersonGraduated`.

Found and fixed on the way: the crew, cast and committee role indexes reported `hasBio: false` for everyone, as the joined `Person.id` was not selected. Covered by tests.

Added on request while doing this: `SiteStats.apiVersion`, the version of nthp-api that built the API, and `SiteStats.buildNumber` and `SiteStats.commit`, the CI run and the commit it was built from, taken from the `GITHUB_RUN_NUMBER` and `GITHUB_SHA` variables GitHub Actions sets itself, and omitted when there are none. `branch` now reads `GITHUB_REF_NAME` too, `BRANCH` still winning where it is set. No workflow change needed in either repo.
