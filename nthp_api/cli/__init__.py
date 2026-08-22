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
    pass


@cli.command()
def version():
    print(f"nthp-api {get_version()}")  # noqa T201


@click.argument("path", type=click.Path(exists=True))
@cli.command()
def load(path):
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
@cli.command()
def lint(path, check_names, verbose, output_format):
    """Report the content's rough edges. Never fails."""
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
@cli.command()
def schema(document_type, output_format):
    """Print the schema for a content document type, or for all of them."""
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
@cli.command()
def validate(paths, verbose, output_format):
    """Check content files against the schema and the per-document rules."""
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
@cli.command()
def new(document_type, identifier):
    """Print a skeleton content file, with every field described."""
    environ["CONTENT_ROOT"] = "does-not-matter"

    from nthp_api.nthp_build import content_schema, skeleton

    click.echo(
        skeleton.render_skeleton(
            content_schema.DOCUMENT_TYPES_BY_NAME[document_type], identifier
        ),
        nl=False,
    )


@cli.command()
def stats():
    environ["CONTENT_ROOT"] = "does-not-matter"

    from nthp_api.nthp_build import database

    database.init_db()
    database.show_stats()


@cli.command()
def smug():
    environ["CONTENT_ROOT"] = "does-not-matter"

    import nthp_api.smugmugger.database
    from nthp_api.nthp_build import database, smugmug

    database.init_db()
    nthp_api.smugmugger.database.init_db()
    smugmug.run()


@cli.command()
def dump():
    environ["CONTENT_ROOT"] = "does-not-matter"

    from nthp_api.nthp_build import database, dumper

    database.init_db()
    dumper.delete_output_dir()
    dumper.dump_all()


@click.argument("path", type=click.Path(exists=True))
@cli.command()
def build(path):
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
