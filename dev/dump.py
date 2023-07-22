from nthp_api.nthp_build import database, dumper, logs

logs.init()
database.init_db()
dumper.delete_output_dir()
dumper.dump_all()
