import logging
from os import environ

import click

from nthp_api.cli import logs

logs.init()


log = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@click.argument("path", type=click.Path(exists=True))
@cli.command()
def load(path):
    environ["CONTENT_ROOT"] = str(path)

    from nthp_api.nthp_build import database, loader

    database.init_db(create=True)
    loader.run_loaders()


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

    from nthp_api.nthp_build.config import settings

    # Ensure that the settings are set correctly, if this breaks we've probably imported
    # settings before setting the env vars.
    assert settings.content_root == path, f"CONTENT_ROOT is {settings.content_root}"

    log.info(f"Building from {path} using in-memory database")

    import nthp_api.smugmugger.database
    from nthp_api.nthp_build import database, dumper, loader, smugmug

    database.init_db(create=True)
    loader.run_loaders()
    database.show_stats()
    nthp_api.smugmugger.database.init_db()
    smugmug.run()
    dumper.delete_output_dir()
    dumper.dump_all()
