# History Project API Generator

This project generates a JSON API from the [history-project](https://github.com/newtheatre/history-project) content repository. It does that in two steps:

- **load**: Generate a sqlite database from the source files.
- **dump**: Use that database to generate a JSON API.

## Endpoints

- The API is currently hosted at <https://nthp-api.newtheatre.org.uk/v1>.
- The specification is available at <https://nthp-api.newtheatre.org.uk/v1/master/openapi.json>.
- Human-readable docs, rendered with Scalar, are at <https://nthp-api.newtheatre.org.uk/v1/master/>.
  ReDoc works too: <https://redocly.github.io/redoc/?url=https://nthp-api.newtheatre.org.uk/v1/master/openapi.json>.

# Usage

## From source

- Ensure you have [uv](https://docs.astral.sh/uv/) installed.
- Run `uv sync`.
- Clone the history project repository into the `content/` directory. You can do a shallow clone for this: `GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --branch master git@github.com:newtheatre/history-project content`.
- Run `./nthp load` to generate the sqlite database from the content files.
- Run `./nthp dump` to generate the API from the database into the `dist/` directory.

## From PyPi

- With pip installed run `pip install --user nthp-api`. If you have your local bin folder on your path you should now be able to run `nthp`.
- Within the history-project repo run `nthp load` to generate the sqlite database from the content files.
- Run `nthp dump` to generate the API from the database into the `dist/` directory.

Alternatively you can run `nthp build` to run both steps in one go.

## The content schema

The ingest models are the authority on what a content file may contain, and the
dump publishes them: `dist/content-schema/{show,person,venue,committee,history,roles,link-types}.json`
as draft 2020-12 JSON Schema, alongside `index.html`, the same tables written
for people to read. Both sit beside `openapi.json` and are versioned with it.

| Command                                        | What it does                                          |
| ---------------------------------------------- | ----------------------------------------------------- |
| `nthp schema [type] [--format json\|markdown]` | Print a schema, or all of them                        |
| `nthp validate <path>…`                        | Check files or directories; nonzero exit on a problem |
| `nthp new show\|person\|venue [--id ID]`       | Print a skeleton with every field described           |

`nthp validate` runs the same models and the same per-document checks as
`nthp load`, so what it accepts is what a build accepts. Anything needing the
whole repository to see belongs to `nthp lint` below.

## Linting the content

`nthp lint <path>` loads the content into an in-memory database and reports what
the archive tolerates but an editor might want to fix: venues referenced without
a document, credits with no name, people who may be one person twice, roles and
link types matching no definition, and so on.

The report is written for whoever edits the content, not for whoever wrote the
generator. Each check gets a heading with its count, a line saying what the
check means and how to fix it, and a table of what it found — the file to open,
the value at fault, and what it costs. A summary table closes the report, with
each check coloured by severity: amber for what is worth fixing, cyan for the
merely advisory.

| Option           | What it does                                                          |
| ---------------- | --------------------------------------------------------------------- |
| `--check NAME`   | Run one check; repeat the option for several. Names are in the report |
| `--verbose`      | List every finding, rather than the first few                         |
| `--format plain` | No colour and no boxes, for a CI log; the default when not a terminal |

Linting never fails: these are expectations, not defects. Defects are reported
as errors by `nthp load` and `nthp build` instead, in the plain logging both use.

## Contributing

### Git hooks

Git hooks are used to lint and format the source code using [ruff](https://docs.astral.sh/ruff/)

- Ensure you have [prek](https://prek.j178.dev/) installed.
- Run `prek install` to install the hooks.
- Run `prek run --all-files` to check everything.

### Tests

Run `uv run pytest`.

## Release

See the `bin/release.sh` script for the release process. This assumes that your local machine has the correct credentials to publish to PyPi.
