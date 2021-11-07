import coloredlogs

from nthp_build import database, loader
from nthp_build.config import settings

coloredlogs.install(level=settings.log_level)

database.init_db(create=True)
loader.run_loaders()
