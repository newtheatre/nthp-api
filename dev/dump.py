import coloredlogs

from nthp_build import database, dumper
from nthp_build.config import settings

coloredlogs.install(level=settings.log_level)

database.init_db()
dumper.delete_output_dir()
dumper.dump_all()
