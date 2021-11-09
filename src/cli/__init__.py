import click

from nthp_build import logging

logging.init()


@click.group()
def cli():
    pass


@cli.command()
def load():
    from nthp_build import database, loader

    database.init_db(create=True)
    loader.run_loaders()


@cli.command()
def stats():
    from nthp_build import database

    database.init_db()
    database.show_stats()


@cli.command()
def dump():
    from nthp_build import database, dumper

    database.init_db()
    dumper.delete_output_dir()
    dumper.dump_all()


@cli.command()
def build():
    from nthp_build.config import settings

    settings.db_uri = ":memory:"

    from nthp_build import database, dumper, loader

    database.init_db(create=True)
    loader.run_loaders()
    database.show_stats()
    dumper.delete_output_dir()
    dumper.dump_all()
