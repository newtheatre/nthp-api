import click
import coloredlogs

from nthp_build import database, dumper, loader
from nthp_build.config import settings

coloredlogs.install(level=settings.log_level)


@click.group()
def cli():
    pass


@cli.command()
def load():
    database.init_db(create=True)
    loader.run_loaders()


@cli.command()
def dump():
    database.init_db()
    dumper.clean_dist()
    dumper.dump_all()
