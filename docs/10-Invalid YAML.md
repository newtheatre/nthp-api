---
type: task
status: done
---

# Catch invalid YAML

PyYAML's SafeLoader silently resolves duplicate mapping keys (last wins), so a
repeated key discards the earlier block without trace. Pydantic never sees the
lost content, so validation cannot catch it. A sweep of the content repo
(2026-08-19, 1,844 documents) found **21 duplicate keys across 19 files**,
including entire `crew`, `trivia`, `assets` and `prod_shots` blocks:

| File                                             | Key          | Lines       |
| ------------------------------------------------ | ------------ | ----------- |
| `_shows/06_07/a_streetcar_named_desire.md`       | `crew`       | 15, 37      |
| `_shows/09_10/only_one_wing.md`                  | `playwright` | 3, 7        |
| `_shows/16_17/dead.md`                           | `trivia`     | 12, 157     |
| `_shows/17_18/quiz_show.md`                      | `prod_shots` | 99, 110     |
| `_shows/17_18/the_effect.md`                     | `trivia`     | 11, 100     |
| `_shows/18_19/the_seagull.md`                    | `trivia`     | 13, 96      |
| `_shows/19_20/corona_cancelled_fringe.md`        | `prod_shots` | 201, 204    |
| `_shows/19_20/corona_cancelled_inhouse.md`       | `prod_shots` | 356, 359, 362 |
| `_shows/19_20/edward_the_second.md`              | `adaptor`    | 4, 5        |
| `_shows/20_21/autumn_showers.md`                 | `name`       | 36, 37      |
| `_shows/21_22/alice.md`                          | `assets`     | 14, 35      |
| `_shows/59_60/coriolanus.md`                     | `role`, `name` | 133–136   |
| `_shows/73_74/tango.md`                          | `name`       | 11, 12      |
| `_shows/75_76/journeys_end.md`                   | `trivia`     | 11, 66      |
| `_people/angharad_davies.md`                     | `graduated`  | 5, 8        |
| `_people/beth_angella.md`                        | `graduated`  | 4, 8        |
| `_people/david_taylor.md`                        | `graduated`  | 3, 5        |
| `_people/ellie_cawthorne.md`                     | `headshot`   | 3, 8        |
| `_people/lucien_jack.md`                         | `graduated`  | 6, 9        |

Not in production yet: **warn, never fail**. Follows the existing pattern in
`loader.py` — log per file, count, summarise, carry on. Parsing semantics
unchanged (last wins), we just make the loss visible.

## Design

### 1. Duplicate-key detection

`nthp_build/yaml_loader.py` (new):

- `class DuplicateKeyDetectingLoader(yaml.SafeLoader)` overriding
  `construct_mapping` (or the mapping-node constructor): walk `node.value` key
  nodes, record duplicates as `(key, first_line, dup_line)` on the loader
  instance using `start_mark`. Applies to every mapping node, so nested
  duplicates are caught too (e.g. `coriolanus.md` duplicates `role`/`name`
  inside a single cast entry). Skip YAML merge keys (`<<`) if ever present.
- A `load_yaml_detecting_duplicates(text) -> tuple[Any, list[DuplicateKey]]`
  helper that instantiates the loader directly (needed to read the collected
  duplicates off the instance — `yaml.load` hides it).

### 2. Wire into both entry points

- **Frontmatter** (`documents.load_document`): subclass
  `frontmatter.default_handlers.YAMLHandler` overriding `load` to use the
  helper; pass the handler to `frontmatter.load`. Verified `YAMLHandler.load`
  takes a `Loader` kwarg in python-frontmatter 1.3.0. Log each duplicate:
  `log.warning("Duplicate key 'crew' in %s (lines 15 and 37); first value discarded")`.
  Line numbers are relative to the frontmatter block; offset to file lines
  since the mark is available.
- **Data files** (`documents.load_yaml`): same helper.

### 3. Parse errors must not crash the loader

`run_document_loader` calls `load_document` with no error handling — one
malformed frontmatter block currently kills the whole loader run (inside a
transaction). Catch `yaml.YAMLError` per document, log with path, count it
alongside `docs_that_failed_validation`, continue.

### 4. Silently-missing frontmatter

A document whose fence is malformed (missing `---`, BOM before it) parses as
zero metadata — content hidden a different way. After `load_document`, if
`document.metadata` is empty but the file is non-trivial, warn. Cheap check,
catches a whole class of "file looks fine, output is empty".

### 5. Adjacent fixes while in `loader.py`

- `run_data_loader`'s `except yaml.YAMLError` is dead code — `load_yaml`
  already swallows the error and returns `None` (which then explodes as a
  `TypeError` in model construction). Let `load_yaml` raise; handle at the
  call site.
- `run_data_loader`'s `except ValidationError` branch calls
  `ValidationError()` with no args — would itself crash. Pass the caught
  error to `print_validation_error`.

### Out of scope

- Type coercion traps (Norway problem, bare-int years): pydantic models and
  `FuzzyDate` already own these — see [04-Strictness review](04-Strictness%20review.md).
- Unknown/missing keys and invalid values stay non-fatal until production.
- Fixing the 19 files in the content repo — separate PR against
  history-project, guided by the table above.

## Tests

Fixture-based, in `tests/test_nthp_build/`:

- duplicate top-level key → warning with both line numbers, last value wins
- duplicate key nested in a list item → caught
- no duplicates → no warnings
- broken frontmatter YAML → document skipped, loader completes
- data file (`history.yaml` shape) duplicate → caught via `load_yaml`

## Follow-ups

- `--strict` flag on `load` turning these warnings (and validation failures)
  into a non-zero exit once production-ready — natural home for the
  [04-Strictness review](04-Strictness%20review.md) items too.
- Content-repo PR fixing the 21 duplicates.

## Decisions

- Land detection first; fix the content repo afterwards, with the warnings
  proving themselves against known-bad data.
- Logging is enough for now; no sqlite build-report recording.

## Task breakdown

1. **Detection core** — `nthp_build/yaml_loader.py`: duplicate-detecting
   loader, `load_yaml_detecting_duplicates` helper, unit tests.
2. **Wire-in** — custom frontmatter handler and `load_yaml` integration in
   `documents.py`, warning logs with file-relative line numbers, tests.
3. **Loader robustness** — per-document `YAMLError` handling, empty-frontmatter
   warning, `run_data_loader` dead-except and `ValidationError()` fixes, tests.
