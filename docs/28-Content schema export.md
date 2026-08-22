---
type: task
status: todo
---

# Content schema export

`history-project/_data/defs/*.yaml` (show, person, venue, committee, year, trivia-list, link-list, person-list, assets, key-events) describe the frontmatter shape for humans, rendered by the Jekyll `def-data.html` include. They are hand-maintained and already drift from what the API accepts (`playwright_alias`, `tour`, `ignore_missing`, `career:` alias, fuzzy dates). The ingest models in `nthp_api/nthp_build/models.py` are now the source of truth; export them so humans and agents can both read the shape and validate what they produce.

## Principle

One source: pydantic ingest models, with `Field(description=…, examples=…)` carrying the prose that lives in `defs/*.yaml` today. Everything below is generated from them; nothing is hand-written twice.

## Outputs

1. **JSON Schema** (draft 2020-12), one file per document type, emitted by the dump into `dist/content-schema/{show,person,venue,committee,year,history,roles,link-types}.json`, so they are published at the API URL alongside `openapi.json` and versioned with it. Generated via `model_json_schema()` after `extra="forbid"` (task 24) so unknown keys are rejected. `FuzzyDate`, `Link`, `PersonRef`, `Asset`, `Trivia` as `$defs` shared across files. Include a top-level `description` per document type (where the file lives, filename → id rule, what the body is).
2. **Human page** `dist/content-schema/index.html` in the docs site (doc 08): per type, a table of field / type / required / description / example, plus a "rules beyond the schema" list (date order, `playwright_alias` needs `student_written`, `devised` xor `playwright`, venue naming → id) sourced from the validator docstrings in task 24. Replaces `def-data.html`.
3. **CLI**
   - `nthp schema [type] [--format json|markdown]` — print a schema, for agents that want it inline.
   - `nthp validate <path>…` — validate one or more content files (frontmatter + body) against the models and the per-document validators, rich output like `nthp lint`, nonzero exit on failure. This is the agent/editor feedback loop: write a page, run validate, fix.
   - `nthp new show|person|venue [--id …]` — emit a skeleton with every field commented, replacing `_shows/_skeleton.md`.
4. **Editor integration** in the content repo: `.vscode/settings.json` mapping `_shows/**/*.md` frontmatter to the published schema URL (via a frontmatter-schema extension), and a short `AGENTS.md` in the content repo pointing at the schema URL, `nthp validate`, and `nthp new`.
5. **Jekyll transition**: until the new site launches the old site still reads `_data/defs/*.yaml`. Add `--format defs-yaml` to `nthp schema` and regenerate those files from the models in the same PR that migrates the descriptions, so the Ruby site keeps rendering without drift. Delete once Jekyll goes.

## Do

- Migrate every `short`/`description` from `defs/*.yaml` into `Field()` on the models; keep `short` as `title`. Audit for fields in defs the models lack and vice versa — each mismatch is either a model gap or a defs lie; resolve, don't paper over.
- Add `dump_content_schema` to `DUMPERS`; tests that every ingest model is exported and that `validate` accepts every file in `content/` that `load` accepts.
- Depends on task 24 (`extra="forbid"`, validators) and pairs with 27 (list playwrights) and 22 (content-side yaml config — those files get schemas too).
