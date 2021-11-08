from nthp_build import database, loader, logging

logging.init()
database.init_db(create=True)
loader.run_loaders()
