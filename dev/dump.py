from nthp_build import database, dumper, logging

logging.init()
database.init_db()
dumper.delete_output_dir()
dumper.dump_all()
