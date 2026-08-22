---
type: task
status: done
---

# Content schema export

`history-project/_data/defs/*.yaml` (show, person, venue, committee, year, trivia-list, link-list, person-list, assets, key-events) describe the frontmatter shape for humans, rendered by the Jekyll `def-data.html` include. They are hand-maintained and already drift from what the API accepts (`playwright_alias`, `tour`, `ignore_missing`, `career:` alias, fuzzy dates). The ingest models in `nthp_api/nthp_build/models.py` are now the source of truth; export them so humans and agents can both read the shape and validate what they produce.

## Principle

One source: pydantic ingest models, with `Field(description=…, examples=…)` carrying the prose that lives in `defs/*.yaml` today. Everything below is generated from them; nothing is hand-written twice.

## Outputs

1. **JSON Schema** (draft 2020-12), one file per document type, emitted by the dump into `dist/content-schema/{show,person,venue,committee,year,history,roles,link-types}.json`, so they are published at the API URL alongside `openapi.json` and versioned with it. Generated via `model_json_schema()` after `extra="forbid"` (task 24) so unknown keys are rejected. `FuzzyDate`, `Link`, `PersonRef`, `Asset`, `Trivia` as `$defs` shared across files. Include a top-level `description` per document type (where the file lives, filename → id rule, what the body is).
2. **Human page** `dist/content-schema/index.html` in the docs site (doc 08): per type, a table of field / type / required / description / example, plus a "rules beyond the schema" list (date order, `playwright_alias` needs `student_written`, `devised` xor `playwright`, venue naming → id) sourced from the validator docstrings in task 24. Replaces `def-data.html`; the old `_data/defs/*.yaml` are deleted, not maintained.
3. **CLI**
   - `nthp schema [type] [--format json|markdown]` — print a schema, for agents that want it inline.
   - `nthp validate <path>…` — validate one or more content files (frontmatter + body) against the models and the per-document validators, rich output like `nthp lint`, nonzero exit on failure. This is the agent/editor feedback loop: write a page, run validate, fix.
   - `nthp new show|person|venue [--id …]` — emit a skeleton with every field commented, replacing `_shows/_skeleton.md`.
4. **Editor integration** in the content repo: `.vscode/settings.json` mapping `_shows/**/*.md` frontmatter to the published schema URL (via a frontmatter-schema extension), and a short `AGENTS.md` in the content repo pointing at the schema URL, `nthp validate`, and `nthp new`.

## Do

- Migrate every `short`/`description` from `defs/*.yaml` into `Field()` on the models; keep `short` as `title`. Audit for fields in defs the models lack and vice versa — each mismatch is either a model gap or a defs lie; resolve, don't paper over.
- Add `dump_content_schema` to `DUMPERS`; tests that every ingest model is exported and that `validate` accepts every file in `content/` that `load` accepts.
- Depends on task 24 (`extra="forbid"`, validators) and pairs with 27 (list playwrights) and 22 (content-side yaml config — those files get schemas too).

## Results

Done in six commits against content at 2026-08-23, verified with
`SMUGMUG_FETCH=false ./nthp build content`.

### What ships

`dist/content-schema/` now carries seven draft 2020-12 schemas —
`show`, `person`, `venue`, `committee`, `history`, `roles`, `link-types` — plus
`index.html`, the page rendering the same tables for people. Each schema is
self-contained: shared shapes (`Link`, `PersonRef`, `Asset`, `Trivia`,
`ShowCanonical`, `TourDate`, `Location`, `PersonAlias`) are `$defs` in every file
that uses them, so an editor can point at one URL and be done. The page hoists
the two shapes more than one type uses into a "Shared shapes" section.

Rules the schema cannot express travel with it as `x-nthp-rules` and are listed
under each type on the page: date order, `date_start` inside its folder's year,
`playwright_alias` needing a student writing credit, `devised` against
`playwright`, the venue naming rule, `venue_sort` without a venue, the filename
rules for people and venues.

### CLI

- `nthp schema [type] [--format json|markdown]` — no type prints all of them.
- `nthp validate <path>…` — files or directories, nonzero exit on a problem.
  It runs the same models and the same per-document checks as the loader, which
  meant moving the show date checks in with the other show defects
  (`shows.get_show_date_defects`) and giving links a defect list
  (`links.get_link_defects`), so both callers read one source. Errors are worded
  by `validation_messages.describe_error`, so `nthp validate` and `nthp load`
  say the same thing about the same file.
- `nthp new show|person|venue [--id …]` — every field commented with what it is
  for, required fields left uncommented so an unedited skeleton fails loudly.
  `--id` names the file to save it as, and fills `title` for a person or venue.

### Audit of `defs/*.yaml` against the models

Every `short` became a `title` and every `description` a `description`, reworded
where the defs described the Jekyll site rather than the API. The mismatches:

- **Defs-only, all `generated: true`** — Jekyll's own output, not authored:
  `path_name`, `placeholder`, `has_bio`, `graduated_estimated`,
  `graduated_actual`, `student`, `decade`, `shows`, `shows_count`, `committees`,
  `committees_count`, `year_page`, `redirect_from`, `seq_*`, `excerpt`, `poster`,
  `display_image` (the show's, not the asset's), `smugmug_album`, `smug_images`,
  `city_sort`, `show_count`, `href_snapshot`, link `icon`. None belong in a
  schema for authored content, so none were added.
- **Defs lies** — `ignore_missing` is marked `generated: true` but the model
  accepts it authored, and does. It is documented as authored.
- **Model-only, real and used** — show `note` and `published`; person `alias`,
  `aliases` and `contact_allowed`; venue `title_short`; link `author`; asset
  `comment`; and `id` on all four document types. All were added by task 24 and
  are now described.
- **`year.yaml` has no schema.** Every one of its fields is `generated: true`
  and there is no `_years/` collection — year pages are built, not authored. The
  task listed `year` among the outputs; it would be an empty file.
- Fuzzy dates: the defs say `YYYY-MM-DD` throughout; the models accept `YYYY` and
  `YYYY-MM` as well, and the schemas say so.

### Editor support

Written into `content/` but deliberately not committed there:

- `.vscode/settings.json` — `yaml.schemas` for the three `_data` files, which
  works today with `redhat.vscode-yaml`. The Markdown front matter entries are
  under `frontMatter.schemas` with a comment saying they need an extension that
  validates front matter; the YAML extension does not. Until one is installed,
  `nthp validate` is the check.
- `.vscode/extensions.json` — recommends `redhat.vscode-yaml`.
- `AGENTS.md` — the "Field definitions" section now points at the schema URL and
  the CLI, and says the schema wins where it and the defs disagree.

### What the content-repo PR should remove

Nothing was deleted from the content repo. A PR there should take out:

- `_data/defs/*.yaml` — all ten files.
- `_includes/def-data.html` and `_includes/def-doc.html`, and their callers:
  `_layouts/{show,person,venue,committee,year}.html` and
  `_content/docs/{show,person,venue,committee,year,link-list,person-list,trivia-list,key-events,photos-and-assets}.md`.
  Those doc pages become a link to the published schema page.
- `_shows/_skeleton.md` and `_people/_skeleton.md`, replaced by `nthp new`.

### Deviations

- No `year.json`, for the reason above.
- `nthp validate` reports exactly what the loader reports for a single file, and
  no more. Rules needing the whole repository — two spellings of a venue, a name
  credited two ways — stay in `nthp lint`, and single-file rules the loader does
  not enforce (a person's `title` against its filename, a venue's slug) are
  documented in `x-nthp-rules` rather than enforced only here. Adding them would
  make `validate` stricter than `load`, which is the one thing it must not be.
