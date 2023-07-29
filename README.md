# History Project API Generator

This project generates a JSON API from the [history-project](https://github.com/newtheatre/history-project) content repository. It does that in two steps:

- **load**: Generate a sqlite database from the source files.
- **dump**: Use that database to generate a JSON API.

## Endpoints

- The API is currently hosted at <https://nthp-api.wjdp.uk/v1>.
- The specification is available at <https://nthp-api.wjdp.uk/v1/master/openapi.json>.
- To render the spec into human-readable docs use a tool such as:
  - ReDoc <https://redocly.github.io/redoc/?url=https://nthp-api.wjdp.uk/v1/master/openapi.json>.
  - Stoplight <https://elements-demo.stoplight.io/?spec=https://nthp-api.wjdp.uk/v1/master/openapi.json>

# Usage

## From source

- Ensure you have [Poetry](https://python-poetry.org/) installed.
- Run `poetry install`.
- Clone the history project repository into the `content/` directory. You can do a shallow clone for this: `GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --branch master git@github.com:newtheatre/history-project content`.
- Run `./nthp load` to generate the sqlite database from the content files.
- Run `./nthp dump` to generate the API from the database into the `dist/` directory.

## From PyPi

- With pip installed run `pip install --user nthp-api`. If you have your local bin folder on your path you should now be able to run `nthp`.
- Within the history-project repo run `nthp load` to generate the sqlite database from the content files.
- Run `nthp dump` to generate the API from the database into the `dist/` directory.

Alternatively you can run `nthp build` to run both steps in one go.

## Contributing

### pre-commit hooks

pre-commit hooks are used to lint the source code using [Black](https://black.readthedocs.io/en/stable/) and [ruff](https://ruff.rs)

- Ensure you have [pre-commit](https://pre-commit.com/) installed.
- Run `pre-commit install` to install pre-commit hooks.

### Tests

Run `pytest` or use the included PyCharm run configuration.

## Release

See the `bin/release.sh` script for the release process. This assumes that your local machine has the correct credentials to publish to PyPi.
