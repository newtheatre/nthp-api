import logging
from os import environ

import click

from nthp_api.cli import logs
from nthp_api.cli.paths import find_content_root
from nthp_api.nthp_build.version import get_version

logs.init()


log = logging.getLogger(__name__)


@click.group()
def cli():
    """Build the New Theatre history JSON API from the content repository."""


@cli.command(short_help="Print the nthp-api version.")
def version():
    """Print the nthp-api version."""
    print(f"nthp-api {get_version()}")  # noqa T201


@click.argument("path", type=click.Path(exists=True))
@cli.command(short_help="Load a content repository into the sqlite database.")
def load(path):
    """Load a content repository into the sqlite database.

    Parses every document under PATH into the database named by DB_URI, then runs
    the build checks. Reports defects; documents that fail validation are skipped.
    """
    environ["CONTENT_ROOT"] = str(path)

    from nthp_api.nthp_build import database, loader, validate

    database.init_db(create=True)
    loader.run_loaders()
    validate.run_build_checks()


@click.option(
    "--check",
    "check_names",
    multiple=True,
    help="Run only these checks, by name; repeatable.",
)
@click.option(
    "--verbose", "-v", is_flag=True, help="List every finding, not just the first few."
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["rich", "plain"]),
    default=None,
    help="Output style. Defaults to plain when not writing to a terminal.",
)
@click.argument("path", type=click.Path(exists=True))
@cli.command(short_help="Report the content's rough edges.")
def lint(path, check_names, verbose, output_format):
    """Report the content's rough edges.

    Loads PATH into an in-memory database and runs every cross-document check:
    spelling variants, namesake collisions, merged people, uncovered crew roles.
    Advisory — it never fails. Use `validate` for per-file defects.
    """
    environ["DB_URI"] = ":memory:"
    environ["CONTENT_ROOT"] = str(path)

    from nthp_api.cli import lint_report
    from nthp_api.nthp_build import database, loader, validate

    unknown = [name for name in check_names if name not in validate.CHECKS_BY_NAME]
    if unknown:
        raise click.BadParameter(
            f"unknown check(s) {', '.join(unknown)}; "
            f"choose from {', '.join(validate.LINT_CHECK_NAMES)}",
            param_hint="--check",
        )

    database.init_db(create=True)
    loader.run_loaders()

    console = lint_report.make_console(plain=output_format == "plain")
    plain = output_format == "plain" or (
        output_format is None and not console.is_terminal
    )
    console = lint_report.make_console(plain=plain)
    lint_report.render_report(
        console,
        validate.run_lint_checks(check_names or None),
        verbose=verbose,
        plain=plain,
    )


@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output style. JSON Schema by default; Markdown to read.",
)
@click.argument("document_type", required=False)
@cli.command(short_help="Print the content schema.")
def schema(document_type, output_format):
    """Print the content schema.

    JSON Schema or Markdown for one content document type (show, person, venue…)
    or for all of them. The same schema is written to dist/content-schema on dump.
    """
    import json

    environ["CONTENT_ROOT"] = "does-not-matter"

    from nthp_api.nthp_build import content_schema, content_schema_docs

    if document_type is not None and document_type not in (
        content_schema.DOCUMENT_TYPES_BY_NAME
    ):
        raise click.BadParameter(
            f"unknown type {document_type}; choose from "
            f"{', '.join(content_schema.DOCUMENT_TYPES_BY_NAME)}",
            param_hint="document_type",
        )
    if output_format == "markdown":
        click.echo(
            content_schema_docs.render_document_type_markdown(
                content_schema.DOCUMENT_TYPES_BY_NAME[document_type]
            )
            if document_type
            else content_schema_docs.render_markdown()
        )
        return
    schemas = content_schema.get_document_schemas()
    click.echo(
        json.dumps(
            schemas[document_type] if document_type else schemas,
            indent=2,
            ensure_ascii=False,
        )
    )


@click.option(
    "--verbose", "-v", is_flag=True, help="Name every file, not only those at fault."
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["rich", "plain"]),
    default=None,
    help="Output style. Defaults to plain when not writing to a terminal.",
)
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@cli.command(short_help="Check content files against the schema.")
def validate(paths, verbose, output_format):
    """Check content files against the schema.

    Runs the models and per-document rules the build uses on each of PATHS, without
    a database, so a file this accepts is a file `build` accepts. Exits non-zero on
    any problem. Whole-repository checks belong to `lint`.
    """
    from pathlib import Path

    given = [Path(path) for path in paths]
    content_root = find_content_root(given[0])
    environ["DB_URI"] = ":memory:"
    environ["CONTENT_ROOT"] = str(content_root or given[0])

    from nthp_api.cli import validate_report
    from nthp_api.nthp_build import content_check, database, loader

    # The loaders narrate themselves; here they are only setting up the checks.
    if not verbose:
        logging.getLogger("nthp_api.nthp_build").setLevel(logging.WARNING)

    database.init_db(create=True)
    if content_root is not None:
        loader.run_data_loaders()
    else:
        log.warning(
            "No content repository found above %s; link types unknown", given[0]
        )

    results = content_check.check_files(given)
    plain = output_format == "plain"
    console = validate_report.make_console(plain=plain)
    plain = plain or (output_format is None and not console.is_terminal)
    console = validate_report.make_console(plain=plain)
    validate_report.render_report(console, results, verbose=verbose, plain=plain)
    if any(not result.ok for result in results):
        raise SystemExit(1)


@click.option("--id", "identifier", default=None, help="Identifier, and so filename.")
@click.argument("document_type", type=click.Choice(["show", "person", "venue"]))
@cli.command(short_help="Print a skeleton content file.")
def new(document_type, identifier):
    """Print a skeleton content file.

    A template for a new DOCUMENT_TYPE (show, person, venue) named IDENTIFIER,
    with every field present and described. Redirect it into the content repo.
    """
    environ["CONTENT_ROOT"] = "does-not-matter"

    from nthp_api.nthp_build import content_schema, skeleton

    click.echo(
        skeleton.render_skeleton(
            content_schema.DOCUMENT_TYPES_BY_NAME[document_type], identifier
        ),
        nl=False,
    )


@cli.command(short_help="Print row counts from the database.")
def stats():
    """Print row counts from the database."""
    environ["CONTENT_ROOT"] = "does-not-matter"

    from nthp_api.nthp_build import database

    database.init_db()
    database.show_stats()


@cli.command(short_help="Fetch SmugMug image data.")
def smug():
    """Fetch SmugMug image data.

    Fetches dimensions for every image the loaded content references into the
    SmugMug cache database. Needs SMUGMUG_API_KEY; skipped with a warning without it.
    """
    environ["CONTENT_ROOT"] = "does-not-matter"

    import nthp_api.smugmugger.database
    from nthp_api.nthp_build import database, smugmug

    database.init_db()
    nthp_api.smugmugger.database.init_db()
    smugmug.run()


@cli.command(short_help="Write the JSON API from the database.")
def dump():
    """Write the JSON API from the database.

    Clears dist/ and writes every endpoint from the database at DB_URI. Run after
    `load` (and `smug`).
    """
    environ["CONTENT_ROOT"] = "does-not-matter"

    from nthp_api.nthp_build import database, dumper

    database.init_db()
    dumper.delete_output_dir()
    dumper.dump_all()


@click.argument("path", type=click.Path(exists=True))
@cli.command(short_help="Load, fetch images and dump in one step.")
def build(path):
    """Load, fetch images and dump in one step.

    Runs load, build checks, the SmugMug fetch and dump from PATH using an in-memory
    database. This is what CI runs.
    """
    # Set settings using environment variables as workers and threads will recreate
    # the settings object and not pick up the values if set here.
    environ["DB_URI"] = ":memory:"
    environ["CONTENT_ROOT"] = str(path)

    log.info(f"Building from {path} using in-memory database")

    import nthp_api.smugmugger.database
    from nthp_api.nthp_build import database, dumper, loader, smugmug, validate

    database.init_db(create=True)
    loader.run_loaders()
    validate.run_build_checks()
    database.show_stats()
    nthp_api.smugmugger.database.init_db()
    smugmug.run()
    dumper.delete_output_dir()
    dumper.dump_all()
