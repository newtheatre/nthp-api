from nthp_api.nthp_build import database, loader, logs

logs.init()
database.init_db(create=True)
loader.run_loaders()
