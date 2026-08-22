---
type: task
status: todo
---

# Multiple playwrights

`playwright:` is a single string. Student-written shows with several writers (`Lawrence Cuthbert and Josh Mallalieu`, `Ian Sheard & Jamie Drew`) get no generated crew credit and no person pages, because the credit generator (task 16) refuses to guess how to split the string. Five shows today: `15_16/sketchy_characters`, `15_16/tsketch_edin`, `15_16/tsketch_stuff`, `16_17/all_the_worlds_a_stage`, `16_17/dead`. Task 24 reports them.

Interim workaround available to editors without any change: `playwright_false: true` plus explicit `crew:` entries with `role: Playwright` per writer.

## Change

Allow a list in content, across the three places that define the field:

1. **Content spec** `history-project/_data/defs/show.yaml`: `playwright` accepts string or list of strings; same for `playwright_alias` (alias per writer, positional or `- name/alias` pairs — choose pairs, positional is fragile). Document in `docs/` of the content repo and the collect/submit form if it offers the field.
2. **Content**: convert the five shows to lists. String form stays valid forever — most shows have one writer.
3. **API** `models.Show`: `playwright: str | list[str]` normalised to `list[str]` at ingest (`playwright_alias` likewise). `PlaywrightShow` descriptor joins for display ("by A and B", Oxford comma for 3+). Crew credit generated per writer; person pages per writer; `/playwrights/index.json` and `/plays/index.json` record one `PlaywrightShow` row per writer so each playwright page lists the show. `ShowDetail.playwright` becomes `playwrights: PlaywrightRef[]` + `playwrightDescriptor` (breaking; fine pre-launch, or keep singular `playwright` as first writer during transition — decide by whether the new site has started).
4. **Search**: `SearchDocumentShow.playwright` text field carries all names.
5. **Validation**: the task 24 "names several people" ERROR is retired; replace with a lint check for string values containing `and`/`&`/`, ` that are not yet lists.

## Not in scope

Non-student multi-author plays (`Kander and Ebb`) — these are descriptors, not people; `student_written: false` already skips credit generation. The list form works for them too, but no content change is needed.
