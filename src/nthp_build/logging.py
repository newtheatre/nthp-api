import logging

import coloredlogs

from nthp_build.config import settings


def init():
    logger = logging.getLogger("nthp_build")
    coloredlogs.install(level=settings.log_level, logger=logger)
