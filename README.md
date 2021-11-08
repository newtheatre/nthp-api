# History Project API Generator

This project generates a JSON API from the [history-project](https://github.com/newtheatre/history-project) content repository. It does that in two steps:

- **load**: Generate a sqlite database from the source files.
- **dump**: Use that database to generate a JSON API.

## Endpoints

- The API is currently hosted at <https://nthp-api.wjdp.uk/v1>.
- The specification is available at <https://nthp-api.wjdp.uk/v1/master/openapi.json>.

## Install

- Ensure you have [Poetry](https://python-poetry.org/) installed.
- Run `poetry install`.

## Running

- Clone the history project repository into the `content/` directory. You can do a shallow clone for this: `GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --branch master git@github.com:newtheatre/history-project content`.
- Run `./nthp load` to generate the sqlite database from the content files.
- Run `./nthp dump` to generate the API from the database into the `dist/` directory.

## Contributing

### pre-commit hooks

pre-commit hooks are used to lint the source code using [Black](https://black.readthedocs.io/en/stable/) and [isort](https://pycqa.github.io/isort/).

- Ensure you have [pre-commit](https://pre-commit.com/) installed.
- Run `pre-commit install` to install pre-commit hooks.

### Tests

Run `pytest` or use the included PyCharm run configuration.
