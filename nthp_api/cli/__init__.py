import logging
from os import environ

import click

from nthp_api.cli import logs
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
