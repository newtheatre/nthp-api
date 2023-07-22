import click

from nthp_api.nthp_build import logs

logs.init()


@click.group()
def cli():
    pass


@cli.command()
def load():
    from nthp_api.nthp_build import database, loader

    database.init_db(create=True)
    loader.run_loaders()


@cli.command()
def stats():
    from nthp_api.nthp_build import database

    database.init_db()
    database.show_stats()


@cli.command()
def smug():
    import nthp_api.smugmugger.database
    from nthp_api.nthp_build import database, smugmug

    database.init_db()
    nthp_api.smugmugger.database.init_db()
    smugmug.run()


@cli.command()
def dump():
    from nthp_api.nthp_build import database, dumper

    database.init_db()
    dumper.delete_output_dir()
    dumper.dump_all()


@cli.command()
def build():
    from nthp_api.nthp_build.config import settings

    settings.db_uri = ":memory:"

    import nthp_api.smugmugger.database
    from nthp_api.nthp_build import database, dumper, loader, smugmug

    database.init_db(create=True)
    loader.run_loaders()
    database.show_stats()
    nthp_api.smugmugger.database.init_db()
    smugmug.run()
    dumper.delete_output_dir()
    dumper.dump_all()
