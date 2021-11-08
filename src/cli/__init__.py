import click

from nthp_build import database, dumper, loader, logging

logging.init()


@click.group()
def cli():
    pass


@cli.command()
def load():
    database.init_db(create=True)
    loader.run_loaders()


@cli.command()
def stats():
    database.init_db()
    database.show_stats()


@cli.command()
def dump():
    database.init_db()
    dumper.delete_output_dir()
    dumper.dump_all()
