---
type: task
status: todo
---

# Content-specific config lives in the content repo

Tasks 12, 13 and 15 hardcoded curation data in the API that editors should own, the way `_data/roles.yaml` already is:

| In API today                                                                                | Move to                                                                                                                                                                    |
| ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `roles.COMMITTEE_ROLE_ALIASES` (8 canonical names, ~10 aliases)                             | `_data/committee-roles.yaml` — same shape as `roles.yaml` (`- role:` + `aliases:`), no icons                                                                               |
| `seasons.SEASON_DEFINITIONS` (14 seasons, merges UNCUT/Fringe→Studio, Unscripted→Creatives) | `_data/seasons.yaml` — `- season:` + `aliases:`; slug still derived by the API                                                                                             |
| `venues.SENTINEL_VENUE_NAMES` (`unknown`, `youtube`)                                        | either `_data/venues.yaml` sentinel list, or just file `_venues/unknown.md` / `_venues/youtube.md` with a `sentinel: true` frontmatter flag (preferred — no new data file) |

Also from task 14: `config.ignore_missing_in_season_ids` and `show_low_crew` mirror `_config.yml` in the content repo — read them from there (`_config.yml` or a `_data/site.yaml`) rather than duplicating.

## Do

- Content repo (`~/local/history-project`, separate PR): add the yaml files / venue documents.
- API: load them at load time like `roles.yaml` (`models.CrewRoleDefinition` pattern, trailing-whitespace stripping, unknown keys ignored), delete the Python constants. Keep a minimal API-side fallback only where the build must not break on missing files — log an error instead.
- Definitions from content should be _the_ list: unrecognised seasons still log; committee roles still generated from `SELECT DISTINCT` with the yaml as alias map.
- Tests switch to fixture yaml.

## Depends on

Content-repo change landing first, or the API reading from a pinned content commit. Sequence after the site-gating tasks (11).
